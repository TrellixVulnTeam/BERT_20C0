from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import copy
import json
import math
import re
import six
import tensorflow as tf
import numpy as np

from utils.bert import bert_utils
from utils.bert import layer_norm_utils
from utils.bert import dropout_utils
from utils.attention_selection import attention_selection_utils
from utils.conv_utils import dynamic_conv_kernel

# from utils.bert.efficient_multihead_attention import efficient_attention_layer

stable_dropout = dropout_utils.ReuseDropout()

def gelu(input_tensor):
	"""Gaussian Error Linear Unit.

	This is a smoother version of the RELU.
	Original paper: https://arxiv.org/abs/1606.08415

	Args:
		input_tensor: float Tensor to perform activation.

	Returns:
		`input_tensor` with the GELU activation applied.
	"""
	cdf = 0.5 * (1.0 + tf.erf(input_tensor / tf.sqrt(2.0)))
	return input_tensor * cdf


def get_activation(activation_string):
	"""Maps a string to a Python function, e.g., "relu" => `tf.nn.relu`.

	Args:
		activation_string: String name of the activation function.

	Returns:
		A Python function corresponding to the activation function. If
		`activation_string` is None, empty, or "linear", this will return None.
		If `activation_string` is not a string, it will return `activation_string`.

	Raises:
		ValueError: The `activation_string` does not correspond to a known
			activation.
	"""

	# We assume that anything that"s not a string is already an activation
	# function, so we just return it.
	if not isinstance(activation_string, six.string_types):
		return activation_string

	if not activation_string:
		return None

	act = activation_string.lower()
	if act == "linear":
		return None
	elif act == "relu":
		return tf.nn.relu
	elif act == "gelu":
		return gelu
	elif act == "tanh":
		return tf.tanh
	else:
		raise ValueError("Unsupported activation: %s" % act)

def dropout(input_tensor, dropout_prob, dropout_name=None):
	"""Perform dropout.

	Args:
		input_tensor: float Tensor.
		dropout_prob: Python float. The probability of dropping out a value (NOT of
			*keeping* a dimension as in `tf.nn.dropout`).

	Returns:
		A version of `input_tensor` with dropout applied.
	"""
	if dropout_prob is None or dropout_prob == 0.0:
		return tf.identity(input_tensor)
	if dropout_name:
		output = stable_dropout.dropout(input_tensor, dropout_prob, dropout_name)
	else:
		output = tf.nn.dropout(input_tensor, 1.0 - dropout_prob)
	return output


def layer_norm(input_tensor, name=None):
	"""Run layer normalization on the last dimension of the tensor."""
	return tf.contrib.layers.layer_norm(
			inputs=input_tensor, begin_norm_axis=-1, begin_params_axis=-1, scope=name)
	# return layer_norm_utils.layer_norm(
	# 		inputs=input_tensor, begin_norm_axis=-1, begin_params_axis=-1, scope=name)


def layer_norm_and_dropout(input_tensor, dropout_prob, name=None, dropout_name=None):
	"""Runs layer normalization followed by dropout."""
	output_tensor = layer_norm(input_tensor, name)
	output_tensor = dropout(output_tensor, dropout_prob, dropout_name=dropout_name)
	return output_tensor


def create_initializer(initializer_range=0.02):
	"""Creates a `truncated_normal_initializer` with the given range."""
	return tf.truncated_normal_initializer(stddev=initializer_range)

def rezero_weight(scope='rezero_weight'):
	with tf.variable_scope(scope, tf.AUTO_REUSE):
		reweight = tf.get_variable(
					"reweight",
					shape=[1],
					initializer=tf.zeros_initializer(),
					trainable=True)
	return reweight

def embedding_lookup(input_ids,
										 vocab_size,
										 embedding_size=128,
										 initializer_range=0.02,
										 word_embedding_name="word_embeddings",
										 use_one_hot_embeddings=False,
										 embedding_table_adv=None):
	"""Looks up words embeddings for id tensor.

	Args:
		input_ids: int32 Tensor of shape [batch_size, seq_length] containing word
			ids.
		vocab_size: int. Size of the embedding vocabulary.
		embedding_size: int. Width of the word embeddings.
		initializer_range: float. Embedding initialization range.
		word_embedding_name: string. Name of the embedding table.
		use_one_hot_embeddings: bool. If True, use one-hot method for word
			embeddings. If False, use `tf.nn.embedding_lookup()`. One hot is better
			for TPUs.

	Returns:
		float Tensor of shape [batch_size, seq_length, embedding_size].
	"""
	# This function assumes that the input is of shape [batch_size, seq_length,
	# num_inputs].
	#
	# If the input is a 2D tensor of shape [batch_size, seq_length], we
	# reshape to [batch_size, seq_length, 1].
	if input_ids.shape.ndims == 2:
		input_ids = tf.expand_dims(input_ids, axis=[-1])

	embedding_table = tf.get_variable(
			name=word_embedding_name,
			shape=[vocab_size, embedding_size],
			initializer=create_initializer(initializer_range))

	if embedding_table_adv is not None:
		embedding_table_adv += embedding_table
		tf.logging.info("==apply adv embedding==")
	else:
		embedding_table_adv = embedding_table
		tf.logging.info("==apply normal embedding==")

	if use_one_hot_embeddings:
		flat_input_ids = tf.reshape(input_ids, [-1])
		one_hot_input_ids = tf.one_hot(flat_input_ids, depth=vocab_size)
		output = tf.matmul(one_hot_input_ids, embedding_table_adv)
	else:
		output = tf.nn.embedding_lookup(embedding_table_adv, input_ids)

	input_shape = bert_utils.get_shape_list(input_ids)

	output = tf.reshape(output,
											input_shape[0:-1] + [input_shape[-1] * embedding_size])
	return (output, embedding_table)

def dense_layer_2d(input_tensor,
									 output_size,
									 initializer,
									 activation,
									 num_attention_heads=1,
									 name=None):
	"""A dense layer with 2D kernel.
	Args:
		input_tensor: Float tensor with rank 3.
		output_size: The size of output dimension.
		initializer: Kernel initializer.
		activation: Activation function.
		num_attention_heads: number of attention head in attention layer.
		name: The name scope of this layer.
	Returns:
		float logits Tensor.
	"""
	del num_attention_heads  # unused
	input_shape = bert_utils.get_shape_list(input_tensor)
	hidden_size = input_shape[2]
	with tf.variable_scope(name):
		w = tf.get_variable(
				name="kernel",
				shape=[hidden_size, output_size],
				initializer=initializer)
		b = tf.get_variable(
				name="bias", shape=[output_size], initializer=tf.zeros_initializer)
		ret = tf.einsum("BFH,HO->BFO", input_tensor, w)
		ret += b
	if activation is not None:
		return activation(ret)
	else:
		return ret

def gumbel_embedding_lookup(input_ids,
										 vocab_size,
										 embedding_size=128,
										 initializer_range=0.02,
										 word_embedding_name="word_embeddings",
										 use_one_hot_embeddings=False,
										 embedding_table_adv=None):
	"""Looks up words embeddings for id tensor.

	Args:
		input_ids: int32 Tensor of shape [batch_size, seq_length] containing word
			ids.
		vocab_size: int. Size of the embedding vocabulary.
		embedding_size: int. Width of the word embeddings.
		initializer_range: float. Embedding initialization range.
		word_embedding_name: string. Name of the embedding table.
		use_one_hot_embeddings: bool. If True, use one-hot method for word
			embeddings. If False, use `tf.nn.embedding_lookup()`. One hot is better
			for TPUs.

	Returns:
		float Tensor of shape [batch_size, seq_length, embedding_size].
	"""
	# This function assumes that the input is of shape [batch_size, seq_length,
	# num_inputs].
	#
	# If the input is a 2D tensor of shape [batch_size, seq_length], we
	# reshape to [batch_size, seq_length, 1].

	input_shape = bert_utils.get_shape_list(input_ids, expected_rank=[3])
	embedding_table = tf.get_variable(
			name=word_embedding_name,
			shape=[vocab_size, embedding_size],
			initializer=create_initializer(initializer_range))
	
	if embedding_table_adv is not None:
		embedding_table_adv += embedding_table
		tf.logging.info("==apply adv embedding==")
	else:
		embedding_table_adv = embedding_table
		tf.logging.info("==apply normal embedding==")
		
	output = tf.einsum("abc,cd->abd", tf.cast(input_ids, tf.float32), embedding_table_adv)
	
	return (output, embedding_table)

def embedding_postprocessor(input_tensor,
														use_token_type=False,
														token_type_ids=None,
														token_type_vocab_size=16,
														token_type_embedding_name="token_type_embeddings",
														use_position_embeddings=True,
														position_embedding_name="position_embeddings",
														initializer_range=0.02,
														max_position_embeddings=512,
														dropout_prob=0.1,
														token_type_ratio=1.0,
														dropout_name=None):
	"""Performs various post-processing on a word embedding tensor.

	Args:
		input_tensor: float Tensor of shape [batch_size, seq_length,
			embedding_size].
		use_token_type: bool. Whether to add embeddings for `token_type_ids`.
		token_type_ids: (optional) int32 Tensor of shape [batch_size, seq_length].
			Must be specified if `use_token_type` is True.
		token_type_vocab_size: int. The vocabulary size of `token_type_ids`.
		token_type_embedding_name: string. The name of the embedding table variable
			for token type ids.
		use_position_embeddings: bool. Whether to add position embeddings for the
			position of each token in the sequence.
		position_embedding_name: string. The name of the embedding table variable
			for positional embeddings.
		initializer_range: float. Range of the weight initialization.
		max_position_embeddings: int. Maximum sequence length that might ever be
			used with this model. This can be longer than the sequence length of
			input_tensor, but cannot be shorter.
		dropout_prob: float. Dropout probability applied to the final output tensor.

	Returns:
		float tensor with same shape as `input_tensor`.

	Raises:
		ValueError: One of the tensor shapes or input values is invalid.
	"""
	input_shape = bert_utils.get_shape_list(input_tensor, expected_rank=3)
	batch_size = input_shape[0]
	seq_length = input_shape[1]
	width = input_shape[2]

	# if seq_length > max_position_embeddings:
	# 	raise ValueError("The seq length (%d) cannot be greater than "
	# 									 "`max_position_embeddings` (%d)" %
	# 									 (seq_length, max_position_embeddings))

	output = input_tensor

	if use_token_type:
		if token_type_ids is None:
			raise ValueError("`token_type_ids` must be specified if"
											 "`use_token_type` is True.")
		token_type_table = tf.get_variable(
				name=token_type_embedding_name,
				shape=[token_type_vocab_size, width],
				initializer=create_initializer(initializer_range))
		# This vocab will be small so we always do one-hot here, since it is always
		# faster for a small vocabulary.
		flat_token_type_ids = tf.reshape(token_type_ids, [-1])
		one_hot_ids = tf.one_hot(flat_token_type_ids, depth=token_type_vocab_size)
		token_type_embeddings = tf.matmul(one_hot_ids, token_type_table)
		token_type_embeddings = tf.reshape(token_type_embeddings,
																			 [batch_size, seq_length, width])
		output += token_type_ratio * token_type_embeddings

	if use_position_embeddings:
		full_position_embeddings = tf.get_variable(
				name=position_embedding_name,
				shape=[max_position_embeddings, width],
				initializer=create_initializer(initializer_range))
		# Since the position embedding table is a learned variable, we create it
		# using a (long) sequence length `max_position_embeddings`. The actual
		# sequence length might be shorter than this, for faster training of
		# tasks that do not have long sequences.
		#
		# So `full_position_embeddings` is effectively an embedding table
		# for position [0, 1, 2, ..., max_position_embeddings-1], and the current
		# sequence has positions [0, 1, 2, ... seq_length-1], so we can just
		# perform a slice.

		# if seq_length < max_position_embeddings:
		# 	position_embeddings = tf.slice(full_position_embeddings, [0, 0],
		# 																 [seq_length, -1])
		# else:
		# 	position_embeddings = full_position_embeddings

		# position_embeddings = tf.cond(tf.less(seq_length, max_position_embeddings), 
		# 												lambda:tf.slice(full_position_embeddings, [0, 0],
		# 																 [seq_length, -1]), 
		# 												lambda:full_position_embeddings)

		flat_pos_ids = tf.range(seq_length, dtype=tf.int32)
		one_hot_pos_ids = tf.one_hot(flat_pos_ids, depth=max_position_embeddings)
		position_embeddings = tf.matmul(one_hot_pos_ids, full_position_embeddings)

		num_dims = len(output.shape.as_list())

		# Only the last two dimensions are relevant (`seq_length` and `width`), so
		# we broadcast among the first dimensions, which is typically just
		# the batch size.
		position_broadcast_shape = []
		for _ in range(num_dims - 2):
			position_broadcast_shape.append(1)
		position_broadcast_shape.extend([seq_length, width])
		position_embeddings = tf.reshape(position_embeddings,
																		 position_broadcast_shape)
		output += position_embeddings

	output = layer_norm_and_dropout(output, dropout_prob, dropout_name=dropout_name)
	return output

def embedding_rule_type_postprocessor(input_tensor,
														use_token_type=False,
														token_type_ids=None,
														rule_type_ids=None,
														token_type_vocab_size=16,
														rule_type_size=2,
														token_type_embedding_name="token_type_embeddings",
														use_position_embeddings=True,
														position_embedding_name="position_embeddings",
														rule_type_embedding_name="rule_type_embedding",
														use_rule_type_embeddings=True,
														initializer_range=0.02,
														max_position_embeddings=512,
														dropout_prob=0.1,
														dropout_name=None):
	"""Performs various post-processing on a word embedding tensor.

	Args:
		input_tensor: float Tensor of shape [batch_size, seq_length,
			embedding_size].
		use_token_type: bool. Whether to add embeddings for `token_type_ids`.
		token_type_ids: (optional) int32 Tensor of shape [batch_size, seq_length].
			Must be specified if `use_token_type` is True.
		token_type_vocab_size: int. The vocabulary size of `token_type_ids`.
		token_type_embedding_name: string. The name of the embedding table variable
			for token type ids.
		use_position_embeddings: bool. Whether to add position embeddings for the
			position of each token in the sequence.
		position_embedding_name: string. The name of the embedding table variable
			for positional embeddings.
		initializer_range: float. Range of the weight initialization.
		max_position_embeddings: int. Maximum sequence length that might ever be
			used with this model. This can be longer than the sequence length of
			input_tensor, but cannot be shorter.
		dropout_prob: float. Dropout probability applied to the final output tensor.

	Returns:
		float tensor with same shape as `input_tensor`.

	Raises:
		ValueError: One of the tensor shapes or input values is invalid.
	"""
	input_shape = bert_utils.get_shape_list(input_tensor, expected_rank=3)
	batch_size = input_shape[0]
	seq_length = input_shape[1]
	width = input_shape[2]

	if seq_length > max_position_embeddings:
		raise ValueError("The seq length (%d) cannot be greater than "
										 "`max_position_embeddings` (%d)" %
										 (seq_length, max_position_embeddings))

	output = input_tensor

	if use_token_type:
		if token_type_ids is None:
			raise ValueError("`token_type_ids` must be specified if"
											 "`use_token_type` is True.")
		token_type_table = tf.get_variable(
				name=token_type_embedding_name,
				shape=[token_type_vocab_size, width],
				initializer=create_initializer(initializer_range))
		# This vocab will be small so we always do one-hot here, since it is always
		# faster for a small vocabulary.
		flat_token_type_ids = tf.reshape(token_type_ids, [-1])
		one_hot_ids = tf.one_hot(flat_token_type_ids, depth=token_type_vocab_size)
		token_type_embeddings = tf.matmul(one_hot_ids, token_type_table)
		token_type_embeddings = tf.reshape(token_type_embeddings,
																			 [batch_size, seq_length, width])
		output += token_type_embeddings

	if use_position_embeddings:
		full_position_embeddings = tf.get_variable(
				name=position_embedding_name,
				shape=[max_position_embeddings, width],
				initializer=create_initializer(initializer_range))
		# Since the position embedding table is a learned variable, we create it
		# using a (long) sequence length `max_position_embeddings`. The actual
		# sequence length might be shorter than this, for faster training of
		# tasks that do not have long sequences.
		#
		# So `full_position_embeddings` is effectively an embedding table
		# for position [0, 1, 2, ..., max_position_embeddings-1], and the current
		# sequence has positions [0, 1, 2, ... seq_length-1], so we can just
		# perform a slice.

		if seq_length < max_position_embeddings:
			position_embeddings = tf.slice(full_position_embeddings, [0, 0],
																		 [seq_length, -1])
		else:
			position_embeddings = full_position_embeddings

		# position_embeddings = tf.cond(tf.less(seq_length, max_position_embeddings), 
		# 												lambda:tf.slice(full_position_embeddings, [0, 0],
		# 																 [seq_length, -1]), 
		# 												lambda:full_position_embeddings)

		num_dims = len(output.shape.as_list())

		# Only the last two dimensions are relevant (`seq_length` and `width`), so
		# we broadcast among the first dimensions, which is typically just
		# the batch size.
		position_broadcast_shape = []
		for _ in range(num_dims - 2):
			position_broadcast_shape.append(1)
		position_broadcast_shape.extend([seq_length, width])
		position_embeddings = tf.reshape(position_embeddings,
																		 position_broadcast_shape)
		output += position_embeddings

	if use_rule_type_embeddings:
		if rule_type_ids is None:
			raise ValueError("`rule_type_ids` must be specified if"
											 "`use_rule_type_embeddings` is True.")
		rule_type_table = tf.get_variable(
				name=rule_type_embedding_name,
				shape=[rule_type_size, width],
				initializer=create_initializer(initializer_range))
		# This vocab will be small so we always do one-hot here, since it is always
		# faster for a small vocabulary.
		flat_rule_type_ids = tf.reshape(rule_type_ids, [-1])
		one_hot_ids = tf.one_hot(flat_rule_type_ids, depth=rule_type_size)
		rule_type_embeddings = tf.matmul(one_hot_ids, rule_type_table)
		rule_type_embeddings = tf.reshape(rule_type_embeddings,
																			 [batch_size, seq_length, width])
		output += rule_type_embeddings

	output = layer_norm_and_dropout(output, dropout_prob, dropout_name=dropout_name)
	return output


def create_attention_mask_from_input_mask(from_tensor, to_mask):
	"""Create 3D attention mask from a 2D tensor mask.

	Args:
		from_tensor: 2D or 3D Tensor of shape [batch_size, from_seq_length, ...].
		to_mask: int32 Tensor of shape [batch_size, to_seq_length].

	Returns:
		float Tensor of shape [batch_size, from_seq_length, to_seq_length].
	"""
	from_shape = bert_utils.get_shape_list(from_tensor, expected_rank=[2, 3])
	batch_size = from_shape[0]
	from_seq_length = from_shape[1]

	to_shape = bert_utils.get_shape_list(to_mask, expected_rank=2)
	to_seq_length = to_shape[1]

	to_mask = tf.cast(
			tf.reshape(to_mask, [batch_size, 1, to_seq_length]), tf.float32)

	# We don't assume that `from_tensor` is a mask (although it could be). We
	# don't actually care if we attend *from* padding tokens (only *to* padding)
	# tokens so we create a tensor of all ones.
	#
	# `broadcast_ones` = [batch_size, from_seq_length, 1]
	broadcast_ones = tf.ones(
			shape=[batch_size, from_seq_length, 1], dtype=tf.float32)

	# Here we broadcast along two dimensions to create the mask.
	mask = broadcast_ones * to_mask

	return mask


def attention_layer(from_tensor,
										to_tensor,
										attention_mask=None,
										num_attention_heads=1,
										size_per_head=512,
										query_act=None,
										key_act=None,
										value_act=None,
										attention_probs_dropout_prob=0.0,
										initializer_range=0.02,
										do_return_2d_tensor=False,
										batch_size=None,
										from_seq_length=None,
										to_seq_length=None,
										attention_fixed_size=None,
										dropout_name=None,
										structural_attentions="none",
										is_training=False):
	"""Performs multi-headed attention from `from_tensor` to `to_tensor`.

	This is an implementation of multi-headed attention based on "Attention
	is all you Need". If `from_tensor` and `to_tensor` are the same, then
	this is self-attention. Each timestep in `from_tensor` attends to the
	corresponding sequence in `to_tensor`, and returns a fixed-with vector.

	This function first projects `from_tensor` into a "query" tensor and
	`to_tensor` into "key" and "value" tensors. These are (effectively) a list
	of tensors of length `num_attention_heads`, where each tensor is of shape
	[batch_size, seq_length, size_per_head].

	Then, the query and key tensors are dot-producted and scaled. These are
	softmaxed to obtain attention probabilities. The value tensors are then
	interpolated by these probabilities, then concatenated back to a single
	tensor and returned.

	In practice, the multi-headed attention are done with transposes and
	reshapes rather than actual separate tensors.

	Args:
		from_tensor: float Tensor of shape [batch_size, from_seq_length,
			from_width].
		to_tensor: float Tensor of shape [batch_size, to_seq_length, to_width].
		attention_mask: (optional) int32 Tensor of shape [batch_size,
			from_seq_length, to_seq_length]. The values should be 1 or 0. The
			attention scores will effectively be set to -infinity for any positions in
			the mask that are 0, and will be unchanged for positions that are 1.
		num_attention_heads: int. Number of attention heads.
		size_per_head: int. Size of each attention head.
		query_act: (optional) Activation function for the query transform.
		key_act: (optional) Activation function for the key transform.
		value_act: (optional) Activation function for the value transform.
		attention_probs_dropout_prob:
		initializer_range: float. Range of the weight initializer.
		do_return_2d_tensor: bool. If True, the output will be of shape [batch_size
			* from_seq_length, num_attention_heads * size_per_head]. If False, the
			output will be of shape [batch_size, from_seq_length, num_attention_heads
			* size_per_head].
		batch_size: (Optional) int. If the input is 2D, this might be the batch size
			of the 3D version of the `from_tensor` and `to_tensor`.
		from_seq_length: (Optional) If the input is 2D, this might be the seq length
			of the 3D version of the `from_tensor`.
		to_seq_length: (Optional) If the input is 2D, this might be the seq length
			of the 3D version of the `to_tensor`.

	Returns:
		float Tensor of shape [batch_size, from_seq_length,
			num_attention_heads * size_per_head]. (If `do_return_2d_tensor` is
			true, this will be of shape [batch_size * from_seq_length,
			num_attention_heads * size_per_head]).

	Raises:
		ValueError: Any of the arguments or tensor shapes are invalid.
	"""

	def transpose_for_scores(input_tensor, batch_size, num_attention_heads,
													 seq_length, width):
		output_tensor = tf.reshape(
				input_tensor, [batch_size, seq_length, num_attention_heads, width])

		output_tensor = tf.transpose(output_tensor, [0, 2, 1, 3])
		return output_tensor

	from_shape = bert_utils.get_shape_list(from_tensor, expected_rank=[2, 3])
	to_shape = bert_utils.get_shape_list(to_tensor, expected_rank=[2, 3])

	if len(from_shape) != len(to_shape):
		raise ValueError(
				"The rank of `from_tensor` must match the rank of `to_tensor`.")

	if len(from_shape) == 3:
		batch_size = from_shape[0]
		from_seq_length = from_shape[1]
		to_seq_length = to_shape[1]
	elif len(from_shape) == 2:
		if (batch_size is None or from_seq_length is None or to_seq_length is None):
			raise ValueError(
					"When passing in rank 2 tensors to attention_layer, the values "
					"for `batch_size`, `from_seq_length`, and `to_seq_length` "
					"must all be specified.")

	# Scalar dimensions referenced here:
	#   B = batch size (number of sequences)
	#   F = `from_tensor` sequence length
	#   T = `to_tensor` sequence length
	#   N = `num_attention_heads`
	#   H = `size_per_head`

	if attention_fixed_size:
		attention_head_size = attention_fixed_size
		tf.logging.info("==apply attention_fixed_size==")
	else:
		attention_head_size = size_per_head
		tf.logging.info("==apply attention_original_size==")

	from_tensor_2d = bert_utils.reshape_to_matrix(from_tensor)
	to_tensor_2d = bert_utils.reshape_to_matrix(to_tensor)

	# `query_layer` = [B*F, N*H]
	query_layer = tf.layers.dense(
			from_tensor_2d,
			num_attention_heads * attention_head_size,
			activation=query_act,
			name="query",
			kernel_initializer=create_initializer(initializer_range))

	# `key_layer` = [B*T, N*H]
	key_layer = tf.layers.dense(
			to_tensor_2d,
			num_attention_heads * attention_head_size,
			activation=key_act,
			name="key",
			kernel_initializer=create_initializer(initializer_range))

	# `value_layer` = [B*T, N*H]
	value_layer = tf.layers.dense(
			to_tensor_2d,
			num_attention_heads * attention_head_size,
			activation=value_act,
			name="value",
			kernel_initializer=create_initializer(initializer_range))

	# `query_layer` = [B, N, F, H]
	query_layer = transpose_for_scores(query_layer, batch_size,
									 num_attention_heads, 
									 from_seq_length,
									 attention_head_size)

	# `key_layer` = [B, N, T, H]
	key_layer = transpose_for_scores(key_layer, batch_size, 
									num_attention_heads,
									to_seq_length, 
									attention_head_size)

	# Take the dot product between "query" and "key" to get the raw
	# attention scores.
	# `attention_scores` = [B, N, F, T]
	attention_scores = tf.matmul(query_layer, key_layer, transpose_b=True)
	attention_scores = tf.multiply(attention_scores,
									1.0 / math.sqrt(float(attention_head_size)))

	if structural_attentions == "structural_attentions":
		# `attention_mask` = [B, 1, F, T]
		tf.logging.info("==apply structural_attentions==")
		if attention_mask is not None:
			attention_mask = tf.expand_dims(attention_mask, axis=[1])
		else:
			attention_mask = None
		if is_training:
			mode = tf.estimator.ModeKeys.TRAIN
		else:
			mode = None
		attention_scores = attention_selection_utils.attention_group_sampling(
							from_tensor, 
							to_tensor,
							attention_mask,
							mode,
							batch_size=batch_size,
							from_seq_length=from_seq_length,
							to_seq_length=to_seq_length,
							num_attention_heads=num_attention_heads,
							size_per_head=attention_head_size,
							initializer_range=initializer_range,
							key_act=key_act,
							query_act=query_act,
							temperatures=0.01,
							sample_type="soft")

	else:
		tf.logging.info("==apply global attention==")
		if attention_mask is not None:
			# `attention_mask` = [B, 1, F, T]
			attention_mask = tf.expand_dims(attention_mask, axis=[1])

			# Since attention_mask is 1.0 for positions we want to attend and 0.0 for
			# masked positions, this operation will create a tensor which is 0.0 for
			# positions we want to attend and -10000.0 for masked positions.
			adder = (1.0 - tf.cast(attention_mask, tf.float32)) * -10000.0

			# Since we are adding it to the raw scores before the softmax, this is
			# effectively the same as removing these entirely.
			attention_scores += adder

	# Normalize the attention scores to probabilities.
	# `attention_probs` = [B, N, F, T]
	# attention_probs = tf.nn.softmax(attention_scores)
	attention_probs = tf.exp(tf.nn.log_softmax(attention_scores))

	# This is actually dropping out entire tokens to attend to, which might
	# seem a bit unusual, but is taken from the original Transformer paper.
	if structural_attentions not in ["structural_attentions"]:
		attention_probs = dropout(attention_probs, attention_probs_dropout_prob, dropout_name=dropout_name)
		tf.logging.info("==apply attention-scores dropout==")
	else:
		tf.logging.info("==not apply attention-scores dropout==")

	# `value_layer` = [B, T, N, H]
	value_layer = tf.reshape(
			value_layer,
			[batch_size, to_seq_length, num_attention_heads, attention_head_size])

	# `value_layer` = [B, N, T, H]
	value_layer = tf.transpose(value_layer, [0, 2, 1, 3])

	# `context_layer` = [B, N, F, H]
	context_layer = tf.matmul(attention_probs, value_layer)

	# `context_layer` = [B, F, N, H]
	context_layer = tf.transpose(context_layer, [0, 2, 1, 3])

	if do_return_2d_tensor:
		# `context_layer` = [B*F, N*V]
		context_layer = tf.reshape(
				context_layer,
				[batch_size * from_seq_length, num_attention_heads * attention_head_size])
	else:
		# `context_layer` = [B, F, N*V]
		context_layer = tf.reshape(
				context_layer,
				[batch_size, from_seq_length, num_attention_heads * attention_head_size])

	return context_layer, attention_scores, value_layer

def efficient_attention_layer(from_tensor,
										to_tensor,
										attention_mask=None,
										num_attention_heads=1,
										size_per_head=512,
										query_act=None,
										key_act=None,
										value_act=None,
										attention_probs_dropout_prob=0.0,
										initializer_range=0.02,
										do_return_2d_tensor=False,
										batch_size=None,
										from_seq_length=None,
										to_seq_length=None,
										attention_fixed_size=None,
										dropout_name=None,
										structural_attentions="none",
										is_training=False):
	"""Performs multi-headed attention from `from_tensor` to `to_tensor`.

	This is an implementation of multi-headed attention based on "Attention
	is all you Need". If `from_tensor` and `to_tensor` are the same, then
	this is self-attention. Each timestep in `from_tensor` attends to the
	corresponding sequence in `to_tensor`, and returns a fixed-with vector.

	This function first projects `from_tensor` into a "query" tensor and
	`to_tensor` into "key" and "value" tensors. These are (effectively) a list
	of tensors of length `num_attention_heads`, where each tensor is of shape
	[batch_size, seq_length, size_per_head].

	Then, the query and key tensors are dot-producted and scaled. These are
	softmaxed to obtain attention probabilities. The value tensors are then
	interpolated by these probabilities, then concatenated back to a single
	tensor and returned.

	In practice, the multi-headed attention are done with transposes and
	reshapes rather than actual separate tensors.

	Args:
		from_tensor: float Tensor of shape [batch_size, from_seq_length,
			from_width].
		to_tensor: float Tensor of shape [batch_size, to_seq_length, to_width].
		attention_mask: (optional) int32 Tensor of shape [batch_size,
			from_seq_length, to_seq_length]. The values should be 1 or 0. The
			attention scores will effectively be set to -infinity for any positions in
			the mask that are 0, and will be unchanged for positions that are 1.
		num_attention_heads: int. Number of attention heads.
		size_per_head: int. Size of each attention head.
		query_act: (optional) Activation function for the query transform.
		key_act: (optional) Activation function for the key transform.
		value_act: (optional) Activation function for the value transform.
		attention_probs_dropout_prob:
		initializer_range: float. Range of the weight initializer.
		do_return_2d_tensor: bool. If True, the output will be of shape [batch_size
			* from_seq_length, num_attention_heads * size_per_head]. If False, the
			output will be of shape [batch_size, from_seq_length, num_attention_heads
			* size_per_head].
		batch_size: (Optional) int. If the input is 2D, this might be the batch size
			of the 3D version of the `from_tensor` and `to_tensor`.
		from_seq_length: (Optional) If the input is 2D, this might be the seq length
			of the 3D version of the `from_tensor`.
		to_seq_length: (Optional) If the input is 2D, this might be the seq length
			of the 3D version of the `to_tensor`.

	Returns:
		float Tensor of shape [batch_size, from_seq_length,
			num_attention_heads * size_per_head]. (If `do_return_2d_tensor` is
			true, this will be of shape [batch_size * from_seq_length,
			num_attention_heads * size_per_head]).

	Raises:
		ValueError: Any of the arguments or tensor shapes are invalid.
	"""

	def transpose_for_scores(input_tensor, batch_size, num_attention_heads,
													 seq_length, width):
		output_tensor = tf.reshape(
				input_tensor, [batch_size, seq_length, num_attention_heads, width])

		output_tensor = tf.transpose(output_tensor, [0, 2, 1, 3])
		return output_tensor

	from_shape = bert_utils.get_shape_list(from_tensor, expected_rank=[2, 3])
	to_shape = bert_utils.get_shape_list(to_tensor, expected_rank=[2, 3])

	if len(from_shape) != len(to_shape):
		raise ValueError(
				"The rank of `from_tensor` must match the rank of `to_tensor`.")

	if len(from_shape) == 3:
		batch_size = from_shape[0]
		from_seq_length = from_shape[1]
		to_seq_length = to_shape[1]
	elif len(from_shape) == 2:
		if (batch_size is None or from_seq_length is None or to_seq_length is None):
			raise ValueError(
					"When passing in rank 2 tensors to attention_layer, the values "
					"for `batch_size`, `from_seq_length`, and `to_seq_length` "
					"must all be specified.")

	# Scalar dimensions referenced here:
	#   B = batch size (number of sequences)
	#   F = `from_tensor` sequence length
	#   T = `to_tensor` sequence length
	#   N = `num_attention_heads`
	#   H = `size_per_head`

	if attention_fixed_size:
		attention_head_size = attention_fixed_size
		tf.logging.info("==apply attention_fixed_size==", str(attention_head_size))
	else:
		attention_head_size = size_per_head
		tf.logging.info("==apply attention_original_size==", str(attention_head_size))

	from_tensor_2d = bert_utils.reshape_to_matrix(from_tensor)
	to_tensor_2d = bert_utils.reshape_to_matrix(to_tensor)

	# `query_layer` = [B*F, N*H]
	query_layer = tf.layers.dense(
			from_tensor_2d,
			num_attention_heads * attention_head_size,
			activation=query_act,
			name="query",
			kernel_initializer=create_initializer(initializer_range))

	# `key_layer` = [B*T, N*H]
	key_layer = tf.layers.dense(
			to_tensor_2d,
			num_attention_heads * attention_head_size,
			activation=key_act,
			name="key",
			kernel_initializer=create_initializer(initializer_range))

	# `value_layer` = [B*T, N*H]
	value_layer = tf.layers.dense(
			to_tensor_2d,
			num_attention_heads * attention_head_size,
			activation=value_act,
			name="value",
			kernel_initializer=create_initializer(initializer_range))

	# softmax(QK^T/sqrt(4))V
	#softmax(Q)softmax(K)^TV

	# `query_layer` = [B, N, F, H]
	query_layer = transpose_for_scores(query_layer, batch_size,
									 num_attention_heads, from_seq_length,
									 attention_head_size)

	# `key_layer` = [B, N, T, H]
	key_layer = transpose_for_scores(key_layer, batch_size, num_attention_heads,
									to_seq_length, attention_head_size)

	# `value_layer` = [B, N, T, H]
	value_layer = transpose_for_scores(value_layer, batch_size, num_attention_heads,
									to_seq_length, attention_head_size)

	# Take the dot product between "query" and "key" to get the raw
	# attention scores.
	# `attention_scores` = [B, N, H, H]<---[B, N, T, H] x [B, N, T, H]
	# key_mask = [B, T, 1, 1]

	attention_mask = tf.cast(tf.expand_dims(attention_mask[:, 0:1, :], axis=[2]), tf.float32)
	attention_mask = tf.cast(tf.expand_dims(attention_mask, axis=[3]), tf.float32)
	# key_mask = [B, 1, T, 1]
	attention_mask = tf.reshape(attention_mask, [batch_size, 1, to_seq_length, 1])
	adder = (1.0 - tf.cast(attention_mask, tf.float32)) * -10000.0
	attention_scores = tf.nn.log_softmax(key_layer+adder, axis=2)
	attention_probs = tf.exp(attention_scores)
	attention_probs = dropout(attention_probs, attention_probs_dropout_prob, dropout_name=dropout_name)
	
	key_value_scores = tf.matmul(attention_probs, value_layer, transpose_a=True)

	# This is actually dropping out entire tokens to attend to, which might
	# seem a bit unusual, but is taken from the original Transformer paper.
	# [B, N, F, H] x [B, N, H, H]--->[B, N, F, H]
	context_layer = tf.matmul(tf.exp(tf.nn.log_softmax(query_layer, axis=-1)), key_value_scores)

	# `context_layer` = [B, F, N, H]
	context_layer = tf.transpose(context_layer, [0, 2, 1, 3])

	if do_return_2d_tensor:
		# `context_layer` = [B*F, N*V]
		context_layer = tf.reshape(
				context_layer,
				[batch_size * from_seq_length, num_attention_heads * attention_head_size])
	else:
		# `context_layer` = [B, F, N*V]
		context_layer = tf.reshape(
				context_layer,
				[batch_size, from_seq_length, num_attention_heads * attention_head_size])

	return context_layer, attention_scores, value_layer

def transformer_efficient_model(input_tensor,
						attention_mask=None,
						hidden_size=768,
						num_hidden_layers=12,
						num_attention_heads=12,
						intermediate_size=3072,
						intermediate_act_fn=gelu,
						hidden_dropout_prob=0.1,
						attention_probs_dropout_prob=0.1,
						initializer_range=0.02,
						do_return_all_layers=False,
						attention_fixed_size=None,
						dropout_name=None,
						structural_attentions="none",
						is_training=False,
						model_config={},
						from_mask=None,
						to_mask=None):
	"""Multi-headed, multi-layer Transformer from "Attention is All You Need".

	This is almost an exact implementation of the original Transformer encoder.

	See the original paper:
	https://arxiv.org/abs/1706.03762

	Also see:
	https://github.com/tensorflow/tensor2tensor/blob/master/tensor2tensor/models/transformer.py

	Args:
		input_tensor: float Tensor of shape [batch_size, seq_length, hidden_size].
		attention_mask: (optional) int32 Tensor of shape [batch_size, seq_length,
			seq_length], with 1 for positions that can be attended to and 0 in
			positions that should not be.
		hidden_size: int. Hidden size of the Transformer.
		num_hidden_layers: int. Number of layers (blocks) in the Transformer.
		num_attention_heads: int. Number of attention heads in the Transformer.
		intermediate_size: int. The size of the "intermediate" (a.k.a., feed
			forward) layer.
		intermediate_act_fn: function. The non-linear activation function to apply
			to the output of the intermediate/feed-forward layer.
		hidden_dropout_prob: float. Dropout probability for the hidden layers.
		attention_probs_dropout_prob: float. Dropout probability of the attention
			probabilities.
		initializer_range: float. Range of the initializer (stddev of truncated
			normal).
		do_return_all_layers: Whether to also return all layers or just the final
			layer.

	Returns:
		float Tensor of shape [batch_size, seq_length, hidden_size], the final
		hidden layer of the Transformer.

	Raises:
		ValueError: A Tensor shape or parameter is invalid.
	"""
	if hidden_size % num_attention_heads != 0:
		raise ValueError(
				"The hidden size (%d) is not a multiple of the number of attention "
				"heads (%d)" % (hidden_size, num_attention_heads))

	attention_head_size = int(hidden_size / num_attention_heads)
	input_shape = bert_utils.get_shape_list(input_tensor, expected_rank=3)
	batch_size = input_shape[0]
	seq_length = input_shape[1]
	input_width = input_shape[2]

	# The Transformer performs sum residuals on all layers so the input needs
	# to be the same as the hidden size.
	# if input_width != hidden_size:
	# 	raise ValueError("The width of the input tensor (%d) != hidden size (%d)" %
	# 									 (input_width, hidden_size))

	if input_width != hidden_size:
		input_tensor = dense_layer_2d(
		input_tensor, hidden_size, create_initializer(initializer_range),
		None, name="embedding_hidden_mapping_in")

		tf.logging.info("==apply embedding linear projection==")

	# We keep the representation as a 2D tensor to avoid re-shaping it back and
	# forth from a 3D tensor to a 2D tensor. Re-shapes are normally free on
	# the GPU/CPU but may not be free on the TPU, so we want to minimize them to
	# help the optimizer.
	prev_output = bert_utils.reshape_to_matrix(input_tensor)

	all_layer_outputs = []
	all_attention_scores = []
	all_value_outputs = []

	for layer_idx in range(num_hidden_layers):
		with tf.variable_scope("layer_%d" % layer_idx):
			layer_input = prev_output

			with tf.variable_scope("attention"):
				attention_heads = []
				with tf.variable_scope("self"):

					if dropout_name:
						attention_dropout_name = dropout_name + "/layer_%d/attention/self" % layer_idx
					else:
						attention_dropout_name = None

					[attention_head, 
					attention_scores,
					value_layer] = efficient_attention_layer(
							from_tensor=layer_input,
							to_tensor=layer_input,
							attention_mask=attention_mask,
							num_attention_heads=num_attention_heads,
							size_per_head=attention_head_size,
							attention_probs_dropout_prob=attention_probs_dropout_prob,
							initializer_range=initializer_range,
							do_return_2d_tensor=True,
							batch_size=batch_size,
							from_seq_length=seq_length,
							to_seq_length=seq_length,
							attention_fixed_size=attention_fixed_size,
							dropout_name=attention_dropout_name)
					attention_heads.append(attention_head)
					all_attention_scores.append(attention_scores)
					all_value_outputs.append(value_layer)

				attention_output = None
				if len(attention_heads) == 1:
					attention_output = attention_heads[0]
				else:
					# In the case where we have other sequences, we just concatenate
					# them to the self-attention head before the projection.
					attention_output = tf.concat(attention_heads, axis=-1)

				# Run a linear projection of `hidden_size` then add a residual
				# with `layer_input`.
				with tf.variable_scope("output"):
					attention_output = tf.layers.dense(
							attention_output,
							hidden_size,
							kernel_initializer=create_initializer(initializer_range))
					
					if dropout_name:
						output_dropout_name = dropout_name + "/layer_%d/attention/output" % layer_idx
					else:
						output_dropout_name = None

					attention_output = dropout(attention_output, hidden_dropout_prob, dropout_name=output_dropout_name)
					attention_output = layer_norm(attention_output + layer_input)

			# The activation is only applied to the "intermediate" hidden layer.
			with tf.variable_scope("intermediate"):
				intermediate_output = tf.layers.dense(
						attention_output,
						intermediate_size,
						activation=intermediate_act_fn,
						kernel_initializer=create_initializer(initializer_range))

			# Down-project back to `hidden_size` then add the residual.
			with tf.variable_scope("output"):

				if dropout_name:
					output_dropout_name = dropout_name + "/layer_%d/output" % layer_idx
				else:
					output_dropout_name = None

				layer_output = tf.layers.dense(
						intermediate_output,
						hidden_size,
						kernel_initializer=create_initializer(initializer_range))
				layer_output = dropout(layer_output, hidden_dropout_prob, dropout_name=output_dropout_name)
				layer_output = layer_norm(layer_output + attention_output)
				prev_output = layer_output
				all_layer_outputs.append(layer_output)

	if do_return_all_layers:
		final_outputs = []
		for layer_output in all_layer_outputs:
			final_output = bert_utils.reshape_from_matrix(layer_output, input_shape)
			final_outputs.append(final_output)
		return final_outputs, all_attention_scores, all_value_outputs
	else:
		final_output = bert_utils.reshape_from_matrix(prev_output, input_shape)
		return final_output, all_attention_scores, all_value_outputs

 
def transformer_model(input_tensor,
						attention_mask=None,
						hidden_size=768,
						num_hidden_layers=12,
						num_attention_heads=12,
						intermediate_size=3072,
						intermediate_act_fn=gelu,
						hidden_dropout_prob=0.1,
						attention_probs_dropout_prob=0.1,
						initializer_range=0.02,
						do_return_all_layers=False,
						attention_fixed_size=None,
						dropout_name=None,
						structural_attentions="none",
						is_training=False,
						model_config={},
						from_mask=None,
						to_mask=None):
	"""Multi-headed, multi-layer Transformer from "Attention is All You Need".

	This is almost an exact implementation of the original Transformer encoder.

	See the original paper:
	https://arxiv.org/abs/1706.03762

	Also see:
	https://github.com/tensorflow/tensor2tensor/blob/master/tensor2tensor/models/transformer.py

	Args:
		input_tensor: float Tensor of shape [batch_size, seq_length, hidden_size].
		attention_mask: (optional) int32 Tensor of shape [batch_size, seq_length,
			seq_length], with 1 for positions that can be attended to and 0 in
			positions that should not be.
		hidden_size: int. Hidden size of the Transformer.
		num_hidden_layers: int. Number of layers (blocks) in the Transformer.
		num_attention_heads: int. Number of attention heads in the Transformer.
		intermediate_size: int. The size of the "intermediate" (a.k.a., feed
			forward) layer.
		intermediate_act_fn: function. The non-linear activation function to apply
			to the output of the intermediate/feed-forward layer.
		hidden_dropout_prob: float. Dropout probability for the hidden layers.
		attention_probs_dropout_prob: float. Dropout probability of the attention
			probabilities.
		initializer_range: float. Range of the initializer (stddev of truncated
			normal).
		do_return_all_layers: Whether to also return all layers or just the final
			layer.

	Returns:
		float Tensor of shape [batch_size, seq_length, hidden_size], the final
		hidden layer of the Transformer.

	Raises:
		ValueError: A Tensor shape or parameter is invalid.
	"""
	if not attention_fixed_size:
		if hidden_size % num_attention_heads != 0:
			raise ValueError(
					"The hidden size (%d) is not a multiple of the number of attention "
					"heads (%d)" % (hidden_size, num_attention_heads))

	attention_head_size = int(hidden_size / num_attention_heads)
	input_shape = bert_utils.get_shape_list(input_tensor, expected_rank=3)
	batch_size = input_shape[0]
	seq_length = input_shape[1]
	input_width = input_shape[2]

	# The Transformer performs sum residuals on all layers so the input needs
	# to be the same as the hidden size.
	# if input_width != hidden_size:
	# 	raise ValueError("The width of the input tensor (%d) != hidden size (%d)" %
	# 									 (input_width, hidden_size))

	if input_width != hidden_size:
		input_tensor = dense_layer_2d(
		input_tensor, hidden_size, create_initializer(initializer_range),
		None, name="embedding_hidden_mapping_in")

		tf.logging.info("==apply embedding linear projection==")

	# We keep the representation as a 2D tensor to avoid re-shaping it back and
	# forth from a 3D tensor to a 2D tensor. Re-shapes are normally free on
	# the GPU/CPU but may not be free on the TPU, so we want to minimize them to
	# help the optimizer.
	prev_output = bert_utils.reshape_to_matrix(input_tensor)

	all_layer_outputs = []
	all_attention_scores = []
	all_value_outputs = []

	for layer_idx in range(num_hidden_layers):
		with tf.variable_scope("layer_%d" % layer_idx):
			layer_input = prev_output

			with tf.variable_scope("attention"):
				attention_heads = []
				with tf.variable_scope("self"):

					if dropout_name:
						attention_dropout_name = dropout_name + "/layer_%d/attention/self" % layer_idx
					else:
						attention_dropout_name = None
					if layer_idx in list(range(num_hidden_layers)):
						structural_attentions_args = structural_attentions
					else:
						structural_attentions_args = "none"
					[attention_head, 
					attention_scores,
					value_layer] = attention_layer(
							from_tensor=layer_input,
							to_tensor=layer_input,
							attention_mask=attention_mask,
							num_attention_heads=num_attention_heads,
							size_per_head=attention_head_size,
							attention_probs_dropout_prob=attention_probs_dropout_prob,
							initializer_range=initializer_range,
							do_return_2d_tensor=True,
							batch_size=batch_size,
							from_seq_length=seq_length,
							to_seq_length=seq_length,
							attention_fixed_size=attention_fixed_size,
							dropout_name=attention_dropout_name,
							structural_attentions=structural_attentions_args,
							is_training=is_training)
					attention_heads.append(attention_head)
					all_attention_scores.append(attention_scores)
					all_value_outputs.append(value_layer)

				attention_output = None
				if len(attention_heads) == 1:
					attention_output = attention_heads[0]
				else:
					# In the case where we have other sequences, we just concatenate
					# them to the self-attention head before the projection.
					attention_output = tf.concat(attention_heads, axis=-1)

				# Run a linear projection of `hidden_size` then add a residual
				# with `layer_input`.
				with tf.variable_scope("output"):

					if dropout_name:
						output_dropout_name = dropout_name + "/layer_%d/attention/output" % layer_idx
					else:
						output_dropout_name = None

					attention_output = tf.layers.dense(
							attention_output,
							hidden_size,
							kernel_initializer=create_initializer(initializer_range))
					attention_output = dropout(attention_output, hidden_dropout_prob, dropout_name=output_dropout_name)
					attention_output = layer_norm(attention_output + layer_input)

			# The activation is only applied to the "intermediate" hidden layer.
			with tf.variable_scope("intermediate"):
				intermediate_output = tf.layers.dense(
						attention_output,
						intermediate_size,
						activation=intermediate_act_fn,
						kernel_initializer=create_initializer(initializer_range))

			# Down-project back to `hidden_size` then add the residual.
			with tf.variable_scope("output"):

				if dropout_name:
					output_dropout_name = dropout_name + "/layer_%d/output" % layer_idx
				else:
					output_dropout_name = None

				layer_output = tf.layers.dense(
						intermediate_output,
						hidden_size,
						kernel_initializer=create_initializer(initializer_range))
				layer_output = dropout(layer_output, hidden_dropout_prob, dropout_name=output_dropout_name)
				layer_output = layer_norm(layer_output + attention_output)
				prev_output = layer_output
				all_layer_outputs.append(layer_output)

	if do_return_all_layers:
		final_outputs = []
		for layer_output in all_layer_outputs:
			final_output = bert_utils.reshape_from_matrix(layer_output, input_shape)
			final_outputs.append(final_output)
		return final_outputs, all_attention_scores, all_value_outputs
	else:
		final_output = bert_utils.reshape_from_matrix(prev_output, input_shape)
		return final_output, all_attention_scores, all_value_outputs

def conv_transformer_model(input_tensor,
						attention_mask=None,
						hidden_size=768,
						num_hidden_layers=12,
						num_attention_heads=12,
						intermediate_size=3072,
						intermediate_act_fn=gelu,
						hidden_dropout_prob=0.1,
						attention_probs_dropout_prob=0.1,
						initializer_range=0.02,
						do_return_all_layers=False,
						attention_fixed_size=None,
						dropout_name=None,
						structural_attentions="none",
						is_training=False,
						model_config={},
						from_mask=None,
						to_mask=None):
	"""Multi-headed, multi-layer Transformer from "Attention is All You Need".

	This is almost an exact implementation of the original Transformer encoder.

	See the original paper:
	https://arxiv.org/abs/1706.03762

	Also see:
	https://github.com/tensorflow/tensor2tensor/blob/master/tensor2tensor/models/transformer.py

	Args:
		input_tensor: float Tensor of shape [batch_size, seq_length, hidden_size].
		attention_mask: (optional) int32 Tensor of shape [batch_size, seq_length,
			seq_length], with 1 for positions that can be attended to and 0 in
			positions that should not be.
		hidden_size: int. Hidden size of the Transformer.
		num_hidden_layers: int. Number of layers (blocks) in the Transformer.
		num_attention_heads: int. Number of attention heads in the Transformer.
		intermediate_size: int. The size of the "intermediate" (a.k.a., feed
			forward) layer.
		intermediate_act_fn: function. The non-linear activation function to apply
			to the output of the intermediate/feed-forward layer.
		hidden_dropout_prob: float. Dropout probability for the hidden layers.
		attention_probs_dropout_prob: float. Dropout probability of the attention
			probabilities.
		initializer_range: float. Range of the initializer (stddev of truncated
			normal).
		do_return_all_layers: Whether to also return all layers or just the final
			layer.

	Returns:
		float Tensor of shape [batch_size, seq_length, hidden_size], the final
		hidden layer of the Transformer.

	Raises:
		ValueError: A Tensor shape or parameter is invalid.
	"""
	if not attention_fixed_size:
		if hidden_size % num_attention_heads != 0:
			raise ValueError(
					"The hidden size (%d) is not a multiple of the number of attention "
					"heads (%d)" % (hidden_size, num_attention_heads))

	if model_config.get("num_attention_heads_scale", True):
		attention_head_size = int(hidden_size / num_attention_heads)
		num_attention_heads = int(num_attention_heads / 2)
		tf.logging.info("==apply numbers of attention-heads scale==")
	elif model_config.get("attention_head_size_scale", False):
		attention_head_size = int(hidden_size / num_attention_heads / 2)
		tf.logging.info("==apply size of attention-heads scale==")
	else:
		attention_head_size = int(hidden_size / num_attention_heads)
		num_attention_heads = int(num_attention_heads / 2)
	
	input_shape = bert_utils.get_shape_list(input_tensor, expected_rank=3)
	batch_size = input_shape[0]
	seq_length = input_shape[1]
	input_width = input_shape[2]

	# The Transformer performs sum residuals on all layers so the input needs
	# to be the same as the hidden size.
	# if input_width != hidden_size:
	# 	raise ValueError("The width of the input tensor (%d) != hidden size (%d)" %
	# 									 (input_width, hidden_size))

	if input_width != hidden_size:
		input_tensor = dense_layer_2d(
		input_tensor, hidden_size, create_initializer(initializer_range),
		None, name="embedding_hidden_mapping_in")

		tf.logging.info("==apply embedding linear projection==")

	# We keep the representation as a 2D tensor to avoid re-shaping it back and
	# forth from a 3D tensor to a 2D tensor. Re-shapes are normally free on
	# the GPU/CPU but may not be free on the TPU, so we want to minimize them to
	# help the optimizer.
	prev_output = bert_utils.reshape_to_matrix(input_tensor)

	all_layer_outputs = []
	all_attention_scores = []
	all_value_outputs = []

	for layer_idx in range(num_hidden_layers):
		with tf.variable_scope("layer_%d" % layer_idx):
			layer_input = prev_output

			with tf.variable_scope("attention"):
				attention_heads = []
				with tf.variable_scope("self"):

					if dropout_name:
						attention_dropout_name = dropout_name + "/layer_%d/attention/self" % layer_idx
					else:
						attention_dropout_name = None
					if layer_idx in list(range(num_hidden_layers)):
						structural_attentions_args = structural_attentions
					else:
						structural_attentions_args = "none"
					[attention_head, 
					attention_scores,
					value_layer] = attention_layer(
							from_tensor=layer_input,
							to_tensor=layer_input,
							attention_mask=attention_mask,
							num_attention_heads=num_attention_heads,
							size_per_head=attention_head_size,
							attention_probs_dropout_prob=attention_probs_dropout_prob,
							initializer_range=initializer_range,
							do_return_2d_tensor=True,
							batch_size=batch_size,
							from_seq_length=seq_length,
							to_seq_length=seq_length,
							attention_fixed_size=attention_fixed_size,
							dropout_name=attention_dropout_name,
							structural_attentions=structural_attentions_args,
							is_training=is_training)

					conv_head = dynamic_conv_kernel.dynamic_conv_layer(
							from_tensor=layer_input,
							to_tensor=layer_input,
							attention_mask=attention_mask,
							from_mask=from_mask,
							to_mask=to_mask,
							num_attention_heads=num_attention_heads,
							size_per_head=attention_head_size,
							attention_probs_dropout_prob=attention_probs_dropout_prob,
							initializer_range=initializer_range,
							do_return_2d_tensor=True,
							batch_size=batch_size,
							from_seq_length=seq_length,
							to_seq_length=seq_length,
							attention_fixed_size=attention_fixed_size,
							dropout_name=attention_dropout_name,
							structural_attentions=structural_attentions_args,
							is_training=is_training,
							kernel_size=model_config.get('kernel_size', 9),
							strides=model_config.get('stride', 1),
							dilation_rate=model_config.get('stride', 1))

					attention_head = tf.concat([attention_head, conv_head], axis=-1)

					attention_heads.append(attention_head)
					all_attention_scores.append(attention_scores)
					all_value_outputs.append(value_layer)

				attention_output = None
				if len(attention_heads) == 1:
					attention_output = attention_heads[0]
				else:
					# In the case where we have other sequences, we just concatenate
					# them to the self-attention head before the projection.
					attention_output = tf.concat(attention_heads, axis=-1)

				# Run a linear projection of `hidden_size` then add a residual
				# with `layer_input`.
				with tf.variable_scope("output"):

					if dropout_name:
						output_dropout_name = dropout_name + "/layer_%d/attention/output" % layer_idx
					else:
						output_dropout_name = None

					attention_output = tf.layers.dense(
							attention_output,
							hidden_size,
							kernel_initializer=create_initializer(initializer_range))
					attention_output = dropout(attention_output, hidden_dropout_prob, dropout_name=output_dropout_name)
					attention_output = layer_norm(attention_output + layer_input)

			# The activation is only applied to the "intermediate" hidden layer.
			with tf.variable_scope("intermediate"):
				intermediate_output = tf.layers.dense(
						attention_output,
						intermediate_size,
						activation=intermediate_act_fn,
						kernel_initializer=create_initializer(initializer_range))

			# Down-project back to `hidden_size` then add the residual.
			with tf.variable_scope("output"):

				if dropout_name:
					output_dropout_name = dropout_name + "/layer_%d/output" % layer_idx
				else:
					output_dropout_name = None

				layer_output = tf.layers.dense(
						intermediate_output,
						hidden_size,
						kernel_initializer=create_initializer(initializer_range))
				layer_output = dropout(layer_output, hidden_dropout_prob, dropout_name=output_dropout_name)
				layer_output = layer_norm(layer_output + attention_output)
				prev_output = layer_output
				all_layer_outputs.append(layer_output)

	if do_return_all_layers:
		final_outputs = []
		for layer_output in all_layer_outputs:
			final_output = bert_utils.reshape_from_matrix(layer_output, input_shape)
			final_outputs.append(final_output)
		return final_outputs, all_attention_scores, all_value_outputs
	else:
		final_output = bert_utils.reshape_from_matrix(prev_output, input_shape)
		return final_output, all_attention_scores, all_value_outputs

def transformer_rezero_model(input_tensor,
						attention_mask=None,
						hidden_size=768,
						num_hidden_layers=12,
						num_attention_heads=12,
						intermediate_size=3072,
						intermediate_act_fn=gelu,
						hidden_dropout_prob=0.1,
						attention_probs_dropout_prob=0.1,
						initializer_range=0.02,
						do_return_all_layers=False,
						attention_fixed_size=None,
						dropout_name=None,
						structural_attentions="none",
						is_training=False,
						model_config={},
						from_mask=None,
						to_mask=None):
	
	"""Multi-headed, multi-layer Transformer from "Attention is All You Need".

	This is almost an exact implementation of the original Transformer encoder.

	See the original paper:
	https://arxiv.org/abs/1706.03762

	Also see:
	https://github.com/tensorflow/tensor2tensor/blob/master/tensor2tensor/models/transformer.py

	Args:
		input_tensor: float Tensor of shape [batch_size, seq_length, hidden_size].
		attention_mask: (optional) int32 Tensor of shape [batch_size, seq_length,
			seq_length], with 1 for positions that can be attended to and 0 in
			positions that should not be.
		hidden_size: int. Hidden size of the Transformer.
		num_hidden_layers: int. Number of layers (blocks) in the Transformer.
		num_attention_heads: int. Number of attention heads in the Transformer.
		intermediate_size: int. The size of the "intermediate" (a.k.a., feed
			forward) layer.
		intermediate_act_fn: function. The non-linear activation function to apply
			to the output of the intermediate/feed-forward layer.
		hidden_dropout_prob: float. Dropout probability for the hidden layers.
		attention_probs_dropout_prob: float. Dropout probability of the attention
			probabilities.
		initializer_range: float. Range of the initializer (stddev of truncated
			normal).
		do_return_all_layers: Whether to also return all layers or just the final
			layer.

	Returns:
		float Tensor of shape [batch_size, seq_length, hidden_size], the final
		hidden layer of the Transformer.

	Raises:
		ValueError: A Tensor shape or parameter is invalid.
	"""
	if hidden_size % num_attention_heads != 0:
		raise ValueError(
				"The hidden size (%d) is not a multiple of the number of attention "
				"heads (%d)" % (hidden_size, num_attention_heads))

	attention_head_size = int(hidden_size / num_attention_heads)
	input_shape = bert_utils.get_shape_list(input_tensor, expected_rank=3)
	batch_size = input_shape[0]
	seq_length = input_shape[1]
	input_width = input_shape[2]

	# The Transformer performs sum residuals on all layers so the input needs
	# to be the same as the hidden size.
	# if input_width != hidden_size:
	# 	raise ValueError("The width of the input tensor (%d) != hidden size (%d)" %
	# 									 (input_width, hidden_size))

	if input_width != hidden_size:
		input_tensor = dense_layer_2d(
		input_tensor, hidden_size, create_initializer(initializer_range),
		None, name="embedding_hidden_mapping_in")

		tf.logging.info("==apply embedding linear projection==")

	# We keep the representation as a 2D tensor to avoid re-shaping it back and
	# forth from a 3D tensor to a 2D tensor. Re-shapes are normally free on
	# the GPU/CPU but may not be free on the TPU, so we want to minimize them to
	# help the optimizer.
	prev_output = bert_utils.reshape_to_matrix(input_tensor)

	all_layer_outputs = []
	all_attention_scores = []
	all_value_outputs = []

	for layer_idx in range(num_hidden_layers):
		with tf.variable_scope("layer_%d" % layer_idx):
			layer_input = prev_output

			reweight = rezero_weight(scope='rezero')

			with tf.variable_scope("attention"):
				attention_heads = []
				with tf.variable_scope("self"):

					if dropout_name:
						attention_dropout_name = dropout_name + "/layer_%d/attention/self" % layer_idx
					else:
						attention_dropout_name = None

					[attention_head, 
					attention_scores,
					value_layer] = attention_layer(
							from_tensor=layer_input,
							to_tensor=layer_input,
							attention_mask=attention_mask,
							num_attention_heads=num_attention_heads,
							size_per_head=attention_head_size,
							attention_probs_dropout_prob=attention_probs_dropout_prob,
							initializer_range=initializer_range,
							do_return_2d_tensor=True,
							batch_size=batch_size,
							from_seq_length=seq_length,
							to_seq_length=seq_length,
							attention_fixed_size=attention_fixed_size,
							dropout_name=attention_dropout_name,
							structural_attentions=structural_attentions,
							is_training=is_training)
					attention_heads.append(attention_head)
					all_attention_scores.append(attention_scores)
					all_value_outputs.append(value_layer)

				attention_output = None
				if len(attention_heads) == 1:
					attention_output = attention_heads[0]
				else:
					# In the case where we have other sequences, we just concatenate
					# them to the self-attention head before the projection.
					attention_output = tf.concat(attention_heads, axis=-1)

				# Run a linear projection of `hidden_size` then add a residual
				# with `layer_input`.
				with tf.variable_scope("output"):

					if dropout_name:
						output_dropout_name = dropout_name + "/layer_%d/attention/output" % layer_idx
					else:
						output_dropout_name = None

					attention_output = tf.layers.dense(
							attention_output,
							hidden_size,
							kernel_initializer=create_initializer(initializer_range))
					attention_output = dropout(attention_output, hidden_dropout_prob, dropout_name=output_dropout_name)
					attention_output = layer_input + reweight * attention_output

					# attention_output = dropout(attention_output, hidden_dropout_prob)
					# attention_output = layer_norm(attention_output + layer_input)

			# The activation is only applied to the "intermediate" hidden layer.
			with tf.variable_scope("intermediate"):
				intermediate_output = tf.layers.dense(
						attention_output,
						intermediate_size,
						activation=intermediate_act_fn,
						kernel_initializer=create_initializer(initializer_range))

			# Down-project back to `hidden_size` then add the residual.
			with tf.variable_scope("output"):

				if dropout_name:
					output_dropout_name = dropout_name + "/layer_%d/output" % layer_idx
				else:
					output_dropout_name = None

				layer_output = tf.layers.dense(
						intermediate_output,
						hidden_size,
						kernel_initializer=create_initializer(initializer_range))
				layer_output = dropout(layer_output, hidden_dropout_prob, dropout_name=output_dropout_name)
				layer_output = attention_output + reweight * layer_output

				# layer_output = dropout(layer_output, hidden_dropout_prob)
				# layer_output = layer_norm(layer_output + attention_output)

				prev_output = layer_output
				all_layer_outputs.append(layer_output)

	if do_return_all_layers:
		final_outputs = []
		for layer_output in all_layer_outputs:
			final_output = bert_utils.reshape_from_matrix(layer_output, input_shape)
			final_outputs.append(final_output)
		return final_outputs, all_attention_scores, all_value_outputs
	else:
		final_output = bert_utils.reshape_from_matrix(prev_output, input_shape)
		return final_output, all_attention_scores, all_value_outputs

def distributed_transformer_model(input_tensor,
						attention_mask=None,
						hidden_size=768,
						num_hidden_layers=12,
						num_attention_heads=12,
						intermediate_size=3072,
						intermediate_act_fn=gelu,
						hidden_dropout_prob=0.1,
						attention_probs_dropout_prob=0.1,
						initializer_range=0.02,
						do_return_all_layers=False,
						gpu_nums=2):
	"""Multi-headed, multi-layer Transformer from "Attention is All You Need".

	This is almost an exact implementation of the original Transformer encoder.

	See the original paper:
	https://arxiv.org/abs/1706.03762

	Also see:
	https://github.com/tensorflow/tensor2tensor/blob/master/tensor2tensor/models/transformer.py

	Args:
		input_tensor: float Tensor of shape [batch_size, seq_length, hidden_size].
		attention_mask: (optional) int32 Tensor of shape [batch_size, seq_length,
			seq_length], with 1 for positions that can be attended to and 0 in
			positions that should not be.
		hidden_size: int. Hidden size of the Transformer.
		num_hidden_layers: int. Number of layers (blocks) in the Transformer.
		num_attention_heads: int. Number of attention heads in the Transformer.
		intermediate_size: int. The size of the "intermediate" (a.k.a., feed
			forward) layer.
		intermediate_act_fn: function. The non-linear activation function to apply
			to the output of the intermediate/feed-forward layer.
		hidden_dropout_prob: float. Dropout probability for the hidden layers.
		attention_probs_dropout_prob: float. Dropout probability of the attention
			probabilities.
		initializer_range: float. Range of the initializer (stddev of truncated
			normal).
		do_return_all_layers: Whether to also return all layers or just the final
			layer.

	Returns:
		float Tensor of shape [batch_size, seq_length, hidden_size], the final
		hidden layer of the Transformer.

	Raises:
		ValueError: A Tensor shape or parameter is invalid.
	"""
	if hidden_size % num_attention_heads != 0:
		raise ValueError(
				"The hidden size (%d) is not a multiple of the number of attention "
				"heads (%d)" % (hidden_size, num_attention_heads))

	attention_head_size = int(hidden_size / num_attention_heads)
	input_shape = bert_utils.get_shape_list(input_tensor, expected_rank=3)
	batch_size = input_shape[0]
	seq_length = input_shape[1]
	input_width = input_shape[2]

	# The Transformer performs sum residuals on all layers so the input needs
	# to be the same as the hidden size.
	if input_width != hidden_size:
		raise ValueError("The width of the input tensor (%d) != hidden size (%d)" %
										 (input_width, hidden_size))

	# We keep the representation as a 2D tensor to avoid re-shaping it back and
	# forth from a 3D tensor to a 2D tensor. Re-shapes are normally free on
	# the GPU/CPU but may not be free on the TPU, so we want to minimize them to
	# help the optimizer.
	prev_output = bert_utils.reshape_to_matrix(input_tensor)

	all_layer_outputs = []

	gpu_partition = int(num_hidden_layers/gpu_nums)

	gpu_id = -1 # gpu_id is started from 0 to gpu_nums

	for layer_idx in range(num_hidden_layers):
		with tf.variable_scope("layer_%d" % layer_idx):
			layer_input = prev_output

			if np.mod(layer_idx, gpu_partition) == 0:
				gpu_id += 1

			with tf.device('/gpu:{}'.format(gpu_id)):

				tf.logging.info(" apply transformer attention {}-th layer on device {} ".format(layer_idx, gpu_id))
				print(" apply transformer attention {}-th layer on device {} ".format(layer_idx, gpu_id))
				
				with tf.variable_scope("attention"):
					attention_heads = []
					with tf.variable_scope("self"):
						attention_head = attention_layer(
								from_tensor=layer_input,
								to_tensor=layer_input,
								attention_mask=attention_mask,
								num_attention_heads=num_attention_heads,
								size_per_head=attention_head_size,
								attention_probs_dropout_prob=attention_probs_dropout_prob,
								initializer_range=initializer_range,
								do_return_2d_tensor=True,
								batch_size=batch_size,
								from_seq_length=seq_length,
								to_seq_length=seq_length)
						attention_heads.append(attention_head)

					attention_output = None
					if len(attention_heads) == 1:
						attention_output = attention_heads[0]
					else:
						# In the case where we have other sequences, we just concatenate
						# them to the self-attention head before the projection.
						attention_output = tf.concat(attention_heads, axis=-1)

					# Run a linear projection of `hidden_size` then add a residual
					# with `layer_input`.
					with tf.variable_scope("output"):
						attention_output = tf.layers.dense(
								attention_output,
								hidden_size,
								kernel_initializer=create_initializer(initializer_range))
						attention_output = dropout(attention_output, hidden_dropout_prob)
						attention_output = layer_norm(attention_output + layer_input)

				# The activation is only applied to the "intermediate" hidden layer.
				with tf.variable_scope("intermediate"):
					intermediate_output = tf.layers.dense(
							attention_output,
							intermediate_size,
							activation=intermediate_act_fn,
							kernel_initializer=create_initializer(initializer_range))

				# Down-project back to `hidden_size` then add the residual.
				with tf.variable_scope("output"):
					layer_output = tf.layers.dense(
							intermediate_output,
							hidden_size,
							kernel_initializer=create_initializer(initializer_range))
					layer_output = dropout(layer_output, hidden_dropout_prob)
					layer_output = layer_norm(layer_output + attention_output)
					prev_output = layer_output
					all_layer_outputs.append(layer_output)

	if do_return_all_layers:
		final_outputs = []
		for layer_output in all_layer_outputs:
			final_output = bert_utils.reshape_from_matrix(layer_output, input_shape)
			final_outputs.append(final_output)
		return final_outputs
	else:
		final_output = bert_utils.reshape_from_matrix(prev_output, input_shape)
		return final_output