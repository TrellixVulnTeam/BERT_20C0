
import tensorflow as tf
import numpy as np
from utils.bert import bert_utils

"""
only implement where to transfer
what to transfer need:
1. attention_score and hidden states score ratio
2. add head weight
"""

def kl_divergence(source_logits, target_logits):
	source_prob = tf.exp(tf.nn.log_softmax(source_logits))
	target_logits = tf.nn.log_softmax(target_logits)

	kl_distance = -tf.reduce_sum(source_prob * target_logits, axis=-1)
	return tf.reduce_mean(kl_distance)

def l2_distance(source_prob, target_prob, axis):
	l2_distance = tf.sqrt(tf.reduce_sum(tf.pow(source_prob-target_prob, 2.0), axis=(axis)))
	return tf.reduce_mean(l2_distance)

def l1_distance(source_prob, target_prob, axis):
	l1_distance = tf.abs(tf.reduce_sum(source_prob-target_prob, axis=axis))
	return tf.reduce_mean(l1_distance)

def attention_score_matching(teacher_score, student_score,
								match_direction=0):

	# Scalar dimensions referenced here:
	#   B = batch size (number of sequences)
	#   F = `from_tensor` sequence length
	#   T = `to_tensor` sequence length
	#   N = `num_attention_heads`
	#   H = `size_per_head`

	# Take the dot product between "query" and "key" to get the raw
	# attention scores.
	# `attention_scores` = [B, N, F, T]

	if match_direction == 0:
		with tf.variable_scope("attention_weights", reuse=tf.AUTO_REUSE): 
			projection_weights = tf.get_variable(
					"attention_score_weights", [len(student_score), len(teacher_score)],
					initializer=tf.constant_initializer(np.ones((len(student_score), len(teacher_score)))/len(teacher_score), dtype=tf.float32)
					)
			normalized_weights = tf.abs(projection_weights) / tf.reduce_sum(tf.abs(projection_weights), axis=-1, keepdims=True)

	else:
		print("===apply teacher model to student model==")

		with tf.variable_scope("attention_weights", reuse=tf.AUTO_REUSE): 
			projection_weights = tf.get_variable(
					"attention_score_weights", [len(student_score), len(teacher_score)],
					initializer=tf.constant_initializer(np.ones((len(student_score), len(teacher_score)))/len(student_score), dtype=tf.float32)
					)
			normalized_weights = tf.abs(projection_weights) / tf.reduce_sum(tf.abs(projection_weights), axis=0, keepdims=True)


	loss = tf.constant(0.0)
	for i in range(len(student_score)):
		student_score_ = student_score[i]
		student_score_ = tf.nn.log_softmax(student_score_)
		for j in range(len(teacher_score)):
			teacher_score_ = teacher_score[j]
			teacher_score_ = tf.nn.log_softmax(teacher_score_)
			weight = normalized_weights[i,j] # normalized to [0,1]
			loss += weight*l1_distance(teacher_score_, student_score_, axis=1)
	loss /= (len(student_score)*len(teacher_score))
	return loss

def hidden_matching(teacher_hidden, student_hidden, match_direction=0):

	teacher_shape = bert_utils.get_shape_list(teacher_hidden[0], expected_rank=[3])
	student_shape = bert_utils.get_shape_list(student_hidden[0], expected_rank=[3])

	if match_direction == 0:

		with tf.variable_scope("attention_weights", reuse=tf.AUTO_REUSE): 
			projection_weights = tf.get_variable(
					"attention_score_weights", [len(student_hidden), len(teacher_hidden)],
					initializer=tf.constant_initializer(np.ones((len(student_hidden), len(teacher_hidden)))/len(teacher_hidden), dtype=tf.float32)
					)
			normalized_weights = tf.abs(projection_weights) / tf.reduce_sum(tf.abs(projection_weights), axis=-1, keepdims=True)

	else:
		print("===apply teacher model to student model==")
		with tf.variable_scope("attention_weights", reuse=tf.AUTO_REUSE): 
			projection_weights = tf.get_variable(
					"attention_score_weights", [len(student_hidden), len(teacher_hidden)],
					initializer=tf.constant_initializer(np.ones((len(student_hidden), len(teacher_hidden)))/len(student_hidden), dtype=tf.float32)
					)
			normalized_weights = tf.abs(projection_weights) / tf.reduce_sum(tf.abs(projection_weights), axis=0, keepdims=True)

	# B X F X H

	def projection_fn(input_tensor):

		with tf.variable_scope("uniformal_mapping/projection", reuse=tf.AUTO_REUSE): 
			projection_weights = tf.get_variable(
				"output_weights", [student_shape[-1], teacher_shape[-1]],
				initializer=tf.truncated_normal_initializer(stddev=0.02)
				)

			input_tensor_projection = tf.einsum("abc,cd->abd", input_tensor, 
												projection_weights)
			return input_tensor_projection

	loss = tf.constant(0.0)
	for i in range(len(student_hidden)):
		student_hidden_ = student_hidden[i]
		student_hidden_ = projection_fn(student_hidden_)
		student_hidden_ = tf.nn.l2_normalize(student_hidden_, axis=-1)
		for j in range(len(teacher_hidden)):
			teacher_hidden_ = teacher_hidden[j]
			teacher_hidden_ = tf.nn.l2_normalize(teacher_hidden_, axis=-1)
			weight = normalized_weights[i,j] # normalized to [0,1]
			loss += weight*l1_distance(student_hidden_, teacher_hidden_, axis=-1)
			# tf.reduce_mean(tf.sqrt(tf.reduce_sum(tf.pow(student_hidden_-teacher_hidden_, 2.0), axis=(-1))))
	loss /= (len(student_hidden)*len(teacher_hidden))
	return loss

def hidden_cls_matching(teacher_hidden, student_hidden, match_direction=0):

	teacher_shape = bert_utils.get_shape_list(teacher_hidden[0], expected_rank=[3])
	student_shape = bert_utils.get_shape_list(student_hidden[0], expected_rank=[3])

	if match_direction == 0:

		with tf.variable_scope("attention_weights", reuse=tf.AUTO_REUSE): 
			projection_weights = tf.get_variable(
					"attention_score_weights", [len(student_hidden), len(teacher_hidden)],
					initializer=tf.constant_initializer(np.ones((len(student_hidden), len(teacher_hidden)))/len(teacher_hidden), dtype=tf.float32)
					)
			normalized_weights = tf.abs(projection_weights) / tf.reduce_sum(tf.abs(projection_weights), axis=-1, keepdims=True)

	else:
		print("===apply teacher model to student model==")
		with tf.variable_scope("attention_weights", reuse=tf.AUTO_REUSE): 
			projection_weights = tf.get_variable(
					"attention_score_weights", [len(student_hidden), len(teacher_hidden)],
					initializer=tf.constant_initializer(np.ones((len(student_hidden), len(teacher_hidden)))/len(student_hidden), dtype=tf.float32)
					)
			normalized_weights = tf.abs(projection_weights) / tf.reduce_sum(tf.abs(projection_weights), axis=0, keepdims=True)

	# B X F X H

	def projection_fn(input_tensor):

		with tf.variable_scope("uniformal_mapping/projection", reuse=tf.AUTO_REUSE): 
			projection_weights = tf.get_variable(
				"output_weights", [student_shape[-1], teacher_shape[-1]],
				initializer=tf.truncated_normal_initializer(stddev=0.02)
				)

			input_tensor_projection = tf.einsum("ac,cd->ad", input_tensor, 
												projection_weights)
			return input_tensor_projection

	loss = tf.constant(0.0)
	for i in range(len(student_hidden)):
		student_hidden_ = student_hidden[i][:,0:1,:]
		student_hidden_ = projection_fn(student_hidden_)
		student_hidden_ = tf.nn.l2_normalize(student_hidden_, axis=-1)
		for j in range(len(teacher_hidden)):
			teacher_hidden_ = teacher_hidden[j][:,0:1,:]
			teacher_hidden_ = tf.nn.l2_normalize(teacher_hidden_, axis=-1)
			weight = normalized_weights[i,j] # normalized to [0,1]
			loss += weight*l1_distance(student_hidden_, teacher_hidden_, axis=-1)
			# tf.reduce_mean(tf.sqrt(tf.reduce_sum(tf.pow(student_hidden_-teacher_hidden_, 2.0), axis=(-1))))
	loss /= (len(student_hidden)*len(teacher_hidden))
	return loss

