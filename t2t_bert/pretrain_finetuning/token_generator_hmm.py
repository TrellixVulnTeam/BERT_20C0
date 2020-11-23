import tensorflow as tf
import numpy as np
from tensorflow.python.ops import tensor_array_ops, control_flow_ops
from utils.bert import bert_utils
from utils.bert import bert_modules, albert_modules

def ngram_prob(ngram, mask_prob):
	z = np.random.geometric(p=0.2, size=10000)
	prob = []
	for i in range(ngram):
		prob.append((z==(i+1)).sum()/10000.0)
	sum_prob = sum(prob)
	expected_ngram = 0
	for i, value in enumerate(prob):
		prob[i] /= sum_prob
		expected_ngram += prob[i] * (i+1)
	print("==expected ngram==", expected_ngram)
	ngram_mask_prob = mask_prob / (expected_ngram+1e-10)
	for i, value in enumerate(prob):
		prob[i] *= (ngram_mask_prob)
	print(prob)

	all_prob = [1-ngram_mask_prob] + prob
	prob_size = int((1+len(prob)) / 2 * len(prob) + 1)

	tran_prob = [0.0]*prob_size
	accum = 0
	tran_prob[0] = all_prob[0]
	tran_prob[1] = all_prob[1]
	for j in range(2, len(all_prob)):
		tran_prob[j+accum] = all_prob[j]
		accum += (j-1)

	hmm_tran_prob = np.ones((prob_size, prob_size)) * np.array([tran_prob])
	for i, value in enumerate(tran_prob):
		if value == 0:
			hmm_tran_prob[i-1] = np.zeros((prob_size, ))
			hmm_tran_prob[i-1][i] = 1
	return tran_prob, hmm_tran_prob

# def dynamic_span_mask(batch_size, seq_len, hmm_tran_prob):
# 	state = tensor_array_ops.TensorArray(dtype=tf.int32, size=seq_len, dynamic_size=False, infer_shape=True)
# 	def hmm_recurrence(i, cur_state, state):
# 		current_prob = tf.gather_nd(hmm_tran_prob, cur_state)+1e-10
# 		next_state = tf.multinomial(tf.log(current_prob), 
# 									num_samples=1, 
# 									output_dtype=tf.int32)
# 		state = state.write(i, next_state)  # indices, [batch_size]
# 		return i+1, next_state, state

# 	_, _, state = tf.while_loop(
# 			cond=lambda i, _1, _2: i < seq_len,
# 			body=hmm_recurrence,
# 			loop_vars=(tf.constant(1, dtype=tf.int32), 
# 					   tf.cast(tf.zeros((batch_size,1)), dtype=tf.int32), 
# 					   state))
# 	state = tf.transpose(state.stack())
# 	span_mask = tf.cast(tf.not_equal(tf.squeeze(state), 0), tf.int32)
# 	print("==span mask shape==", span_mask.get_shape())
# 	return state, span_mask

def dynamic_span_mask_v1(batch_size, seq_len, hmm_tran_prob):
	state = tf.zeros((batch_size, 1), dtype=tf.int32)
	tran_size = bert_utils.get_shape_list(hmm_tran_prob, expected_rank=[2])
	init_state_prob = tf.random_uniform([batch_size, tran_size[0]],
							minval=0.0,
							maxval=10.0,
							dtype=tf.float32)
	valid_init_state_mask = tf.expand_dims(tf.cast(tf.not_equal(hmm_tran_prob, 0)[:,0], tf.float32), axis=0)
	init_state_prob *= valid_init_state_mask
	init_state = tf.multinomial(tf.log(init_state_prob)+1e-10,
							num_samples=1,
							output_dtype=tf.int32) # batch x 1
		
	print(batch_size, seq_len)
	def hmm_recurrence(i, cur_state, state):
		current_prob = tf.gather_nd(hmm_tran_prob, cur_state)
		print("===prob shape==", current_prob.get_shape())
		next_state = tf.multinomial(tf.log(current_prob+1e-10), 
									num_samples=1, 
									output_dtype=tf.int32)
		state = tf.concat([state, next_state], axis=-1)
		print("state shape==", state.get_shape())
				
#         state = state.write(i, next_state)  # indices, [batch_size]
		return i+1, next_state, state

	_, _, state = tf.while_loop(
			cond=lambda i, _1, _2: i < seq_len,
			body=hmm_recurrence,
			loop_vars=(1, init_state, state),
			parallel_iterations=1,
			back_prop=False,
			shape_invariants=(tf.TensorShape(None), tf.TensorShape([None,None]), tf.TensorShape([None, None]))
			)
	span_mask = tf.cast(tf.not_equal(state, 0), tf.int32)
	return state, span_mask

def dynamic_span_mask_v2(batch_size, seq_len, hmm_tran_prob):
	state = tf.zeros((batch_size, seq_len), dtype=tf.int32)
	tran_size = bert_utils.get_shape_list(hmm_tran_prob, expected_rank=[2])
	init_state_prob = tf.random_uniform([batch_size, tran_size[0]],
							minval=0.0,
							maxval=10.0,
							dtype=tf.float32)
	valid_init_state_mask = tf.expand_dims(tf.cast(tf.not_equal(hmm_tran_prob, 0)[:,0], tf.float32), axis=0)
	init_state_prob *= valid_init_state_mask
	init_state = tf.multinomial(tf.log(init_state_prob)+1e-10,
							num_samples=1,
							output_dtype=tf.int32) # batch x 1

	def hmm_recurrence(i, cur_state, state):
		current_prob = tf.gather_nd(hmm_tran_prob, cur_state)
		next_state = tf.multinomial(tf.log(current_prob+1e-10), 
									num_samples=1, 
									output_dtype=tf.int32)
		mask = tf.expand_dims(tf.one_hot(i, seq_len), axis=0)
		state = state + tf.cast(mask, tf.int32) * next_state
		return i+1, next_state, state

	_, _, state = tf.while_loop(
			cond=lambda i, _1, _2: i < seq_len,
			body=hmm_recurrence,
			loop_vars=(1, init_state, state),
			back_prop=False,
			)
	span_mask = tf.cast(tf.not_equal(state, 0), tf.int32)
	return state, span_mask

def static_span_mask(batch_size, seq_len, hmm_tran_prob):
	state_seq = []
	tran_size = bert_utils.get_shape_list(hmm_tran_prob, expected_rank=[2])
	valid_init_state_mask = tf.expand_dims(tf.cast(tf.not_equal(hmm_tran_prob, 0)[:,0], tf.float32), axis=0)
	init_state_prob = tf.random_uniform([batch_size, tran_size[0]],
							minval=0.0,
							maxval=10.0,
							dtype=tf.float32)
	init_state_prob *= valid_init_state_mask
	cur_state = tf.multinomial(tf.log(init_state_prob)+1e-10,
							num_samples=1,
							output_dtype=tf.int32) # batch x 1
	# cur_state = tf.cast(start_index*tf.ones((batch_size, 1)), dtype=tf.int32)
	def hmm_recurrence(i, cur_state):
		current_prob = tf.gather_nd(hmm_tran_prob, cur_state)
		next_state = tf.multinomial(tf.log(current_prob+1e-10), 
									num_samples=1, 
									output_dtype=tf.int32)
		return i+1, next_state
	for i in range(seq_len):
		_, state = hmm_recurrence(i, cur_state)
		state_seq.append(tf.squeeze(state))

	state = tf.stack(state_seq, axis=1)
	span_mask = tf.cast(tf.not_equal(state,0), tf.int32)
	return state, span_mask

def random_uniform_mask(batch_size, seq_len, mask_probability):
	sample_probs = mask_probability * tf.ones((batch_size, seq_len), dtype=tf.float32)
	noise_dist = tf.distributions.Bernoulli(probs=sample_probs, dtype=tf.float32)
	uniform_mask = noise_dist.sample()
	uniform_mask = tf.cast(uniform_mask, tf.int32)
	return uniform_mask

def mask_method(batch_size, seq_len, hmm_tran_prob_list, **kargs):
	mask_probability = kargs.get("mask_probability", 0.2)
	mask_prior = kargs.get("mask_prior", None)

	span_mask_matrix = []
	print(hmm_tran_prob_list)
	for i, hmm_tran_prob in enumerate(hmm_tran_prob_list):
		state, span_mask = dynamic_span_mask_v2(batch_size, seq_len, hmm_tran_prob)
		# state, span_mask = static_span_mask(batch_size, seq_len, hmm_tran_prob)
		print(span_mask.get_shape(), i)
		span_mask_matrix.append(span_mask)
	uniform_mask = random_uniform_mask(batch_size, seq_len, mask_probability)
	span_mask_matrix.append(uniform_mask)

	span_mask_matrix = tf.stack(span_mask_matrix, axis=1) # [batch, len(hmm_tran_prob_list), seq]
	print(span_mask_matrix.get_shape(), "=====")
	if mask_prior is not None:
		mask_prob = tf.tile(tf.expand_dims(mask_prior, 0), [batch_size, 1])
		tf.logging.info("**** apply predefined mask sample prob **** ")
	else:
		mask_prob = tf.random_uniform([batch_size, len(hmm_tran_prob_list)+1],
							minval=0.0,
							maxval=10.0,
							dtype=tf.float32)
		tf.logging.info("**** apply uniform mask sample prob **** ")
	span_mask_idx = tf.multinomial(tf.log(mask_prob)+1e-10,
							num_samples=1,
							output_dtype=tf.int32) # batch x 1
	
	batch_idx = tf.expand_dims(tf.cast(tf.range(batch_size), tf.int32), axis=-1)
	gather_index = tf.concat([batch_idx, span_mask_idx], axis=-1)
	mixed_random_mask = tf.gather_nd(span_mask_matrix, gather_index)
	print(mixed_random_mask.get_shape(), "==mix random mask shape==")
	tf.logging.info("==applying hmm, unigram, ngram mixture mask sampling==")
	return mixed_random_mask

def hmm_input_ids_generation(config,
							input_ori_ids,
							input_mask,
							hmm_tran_prob_list,
							**kargs):

	mask_id = kargs.get('mask_id', 103)

	input_ori_ids = tf.cast(input_ori_ids, tf.int32)
	input_mask = tf.cast(input_mask, tf.int32)

	unk_mask = tf.cast(tf.math.equal(input_ori_ids, 100), tf.float32) # not replace unk
	cls_mask =  tf.cast(tf.math.equal(input_ori_ids, 101), tf.float32) # not replace cls
	sep_mask = tf.cast(tf.math.equal(input_ori_ids, 102), tf.float32) # not replace sep

	none_replace_mask =  unk_mask + cls_mask + sep_mask
	mask_probability = kargs.get("mask_probability", 0.2)
	replace_probability = kargs.get("replace_probability", 0.1)
	original_probability = kargs.get("original_probability", 0.1)

	input_shape_list = bert_utils.get_shape_list(input_mask, expected_rank=2)
	batch_size = input_shape_list[0]
	seq_length = input_shape_list[1]
		
	tf.logging.info("**** apply fixed_mask_prob %s **** ", str(mask_probability))
	tf.logging.info("**** apply replace_probability %s **** ", str(replace_probability))
	tf.logging.info("**** apply original_probability %s **** ", str(original_probability))

	# state, sampled_binary_mask = dynamic_span_mask_v1(batch_size, seq_length, hmm_tran_prob_list[0])
	sampled_binary_mask = mask_method(batch_size, seq_length, hmm_tran_prob_list, **kargs)

	sampled_binary_mask = input_mask * (1 - tf.cast(none_replace_mask, tf.int32)) * sampled_binary_mask
	sampled_binary_mask = tf.cast(sampled_binary_mask, tf.float32)

	replace_binary_probs = replace_probability * (sampled_binary_mask) # use 10% [mask] to replace token
	replace_noise_dist = tf.distributions.Bernoulli(probs=replace_binary_probs, dtype=tf.float32)
	sampled_replace_binary_mask = replace_noise_dist.sample()
	sampled_replace_binary_mask = tf.cast(sampled_replace_binary_mask, tf.float32)

	ori_binary_probs = original_probability * (sampled_binary_mask - sampled_replace_binary_mask)
	ori_noise_dist = tf.distributions.Bernoulli(probs=ori_binary_probs, dtype=tf.float32)
	sampled_ori_binary_mask = ori_noise_dist.sample()
	sampled_ori_binary_mask = tf.cast(sampled_ori_binary_mask, tf.float32)

	sampled_mask_binary_mask = (sampled_binary_mask - sampled_replace_binary_mask - sampled_ori_binary_mask)
	sampled_mask_binary_mask = tf.cast(sampled_mask_binary_mask, tf.float32)

	vocab_sample_logits = tf.random.uniform(
							[batch_size, seq_length, config.vocab_size],
							minval=0.0,
							maxval=10.0,
							dtype=tf.float32)

	vocab_sample_logits = tf.nn.log_softmax(vocab_sample_logits)
	flatten_vocab_sample_logits = tf.reshape(vocab_sample_logits, 
											[batch_size*seq_length, -1])

	# sampled_logprob_temp, sampled_logprob = gumbel_softmax(flatten_vocab_sample_logits, 
	# 									temperature=0.1,
	# 									samples=config.get('gen_sample', 1))

	# sample_vocab_ids = tf.argmax(sampled_logprob, axis=1) # batch x seq

	sample_vocab_ids = tf.multinomial(flatten_vocab_sample_logits, 
								num_samples=config.get('gen_sample', 1), 
								output_dtype=tf.int32)

	sample_vocab_ids = tf.reshape(sample_vocab_ids, [batch_size, seq_length])
	sample_vocab_ids = tf.cast(sample_vocab_ids, tf.float32)
	input_ori_ids = tf.cast(input_ori_ids, tf.float32)

	output_input_ids = mask_id * tf.cast(sampled_mask_binary_mask, tf.float32) * tf.ones_like(input_ori_ids)
	output_input_ids += sample_vocab_ids * tf.cast(sampled_replace_binary_mask, tf.float32)
	output_input_ids += (1 - tf.cast(sampled_mask_binary_mask + sampled_replace_binary_mask, tf.float32)) * input_ori_ids
	output_sampled_binary_mask = sampled_mask_binary_mask + sampled_replace_binary_mask + sampled_ori_binary_mask

	print("===output_input_ids shape===", output_input_ids.get_shape())
	input_shape_list = bert_utils.get_shape_list(output_input_ids, expected_rank=2)
	print("==input shape list==", input_shape_list)

	output_sampled_binary_mask = tf.cast(output_sampled_binary_mask, tf.int32)
	if not kargs.get('use_tpu', True):
		tf.summary.scalar('mask_ratio', 
		tf.reduce_sum(tf.cast(output_sampled_binary_mask, tf.float32))/(1e-10+tf.cast(tf.reduce_sum(input_mask), dtype=tf.float32)))

	return [tf.cast(output_input_ids, tf.int32), 
				output_sampled_binary_mask]
