import tensorflow as tf

def data_interface(FLAGS):
	print(FLAGS.model_type, "===model type===", FLAGS.task_type)
	if FLAGS.model_type in ["bert","bert_small", "albert", "electra_gumbel_encoder", 
						"albert_official", "bert_seq"]:
		if FLAGS.task_type == "single_sentence_classification":
			name_to_features = {
					"input_ids":
							tf.FixedLenFeature([FLAGS.max_length], tf.int64),
					"input_mask":
							tf.FixedLenFeature([FLAGS.max_length], tf.int64),
					"segment_ids":
							tf.FixedLenFeature([FLAGS.max_length], tf.int64),
					"label_ids":
							tf.FixedLenFeature([], tf.int64),
			}
		elif FLAGS.task_type == "single_sentence_multilabel_classification":
			name_to_features = {
					"input_ids":
							tf.FixedLenFeature([FLAGS.max_length], tf.int64),
					"input_mask":
							tf.FixedLenFeature([FLAGS.max_length], tf.int64),
					"segment_ids":
							tf.FixedLenFeature([FLAGS.max_length], tf.int64),
					"label_ids":
							tf.FixedLenFeature([FLAGS.num_classes], tf.int64),
			}
		elif FLAGS.task_type == "pair_sentence_classification":
			name_to_features = {
				"input_ids_a":
						tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"input_mask_a":
						tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"segment_ids_a":
						tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"input_ids_b":
						tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"input_mask_b":
						tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"segment_ids_b":
						tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"label_ids":
						tf.FixedLenFeature([], tf.int64),
				}
		elif FLAGS.task_type in ['bert_pretrain']:
			name_to_features = {
				"input_ids":
					tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"input_mask":
					tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"segment_ids":
					tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"masked_lm_positions":
					tf.FixedLenFeature([FLAGS.max_predictions_per_seq], tf.int64),
				"masked_lm_ids":
					tf.FixedLenFeature([FLAGS.max_predictions_per_seq], tf.int64),
				"masked_lm_weights":
					tf.FixedLenFeature([FLAGS.max_predictions_per_seq], tf.float32),
				"next_sentence_labels":
					tf.FixedLenFeature([], tf.int64),
				}
		elif FLAGS.task_type in ['bert_seq_lm']:
			if FLAGS.random_generator == "1": 
				name_to_features = {
					"input_ids":
						tf.FixedLenFeature([FLAGS.max_length], tf.int64),
					"input_mask":
						tf.FixedLenFeature([FLAGS.max_length], tf.int64),
					"segment_ids":
						tf.FixedLenFeature([FLAGS.max_length], tf.int64),
					"input_ori_ids":
						tf.FixedLenFeature([FLAGS.max_length], tf.int64),
					"masked_lm_positions":
						tf.FixedLenFeature([FLAGS.max_predictions_per_seq], tf.int64),
					"masked_lm_ids":
						tf.FixedLenFeature([FLAGS.max_predictions_per_seq], tf.int64),
					"masked_lm_weights":
						tf.FixedLenFeature([FLAGS.max_predictions_per_seq], tf.float32),
					"next_sentence_labels":
						tf.FixedLenFeature([], tf.int64),
				}
			elif FLAGS.random_generator == "2":
				name_to_features = {
				"input_ids":
					tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"input_mask":
					tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"segment_ids":
					tf.FixedLenFeature([FLAGS.max_length], tf.int64)
				} 
		elif FLAGS.task_type in ['bert_chid']:
			 name_to_features = {
				"input_ids":
					tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"segment_ids":
					tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"label_positions":
					tf.FixedLenFeature([FLAGS.max_predictions_per_seq], tf.int64),
				"label_ids":
					tf.FixedLenFeature([FLAGS.max_predictions_per_seq], tf.int64),
				"label_weights":
					tf.FixedLenFeature([FLAGS.max_predictions_per_seq], tf.int64),
				}
		elif FLAGS.task_type in ['bert_chid_crf']:
			 name_to_features = {
				"input_ids_a":
					tf.FixedLenFeature([FLAGS.max_length*FLAGS.max_predictions_per_seq], tf.int64),
				"segment_ids_a":
					tf.FixedLenFeature([FLAGS.max_length*FLAGS.max_predictions_per_seq], tf.int64),
				"input_ids_b":
					tf.FixedLenFeature([(FLAGS.num_classes)*FLAGS.max_predictions_per_seq], tf.int64),
				"segment_ids_b":
					tf.FixedLenFeature([(FLAGS.num_classes)*FLAGS.max_predictions_per_seq], tf.int64),
				"label_positions":
					tf.FixedLenFeature([FLAGS.max_predictions_per_seq], tf.int64),
				"label_ids":
					tf.FixedLenFeature([FLAGS.max_predictions_per_seq], tf.int64),
				"label_weights":
					tf.FixedLenFeature([FLAGS.max_predictions_per_seq], tf.int64),
				}

	elif FLAGS.model_type in ["bert_rule"]:
		if FLAGS.task_type == "single_sentence_classification":
			name_to_features = {
					"input_ids":
							tf.FixedLenFeature([FLAGS.max_length], tf.int64),
					"input_mask":
							tf.FixedLenFeature([FLAGS.max_length], tf.int64),
					"segment_ids":
							tf.FixedLenFeature([FLAGS.max_length], tf.int64),
					"rule_ids":
							tf.FixedLenFeature([FLAGS.max_length], tf.int64),
					"label_ids":
							tf.FixedLenFeature([], tf.int64),
			}

	elif FLAGS.model_type in ["textcnn", "textlstm", "dan"]:
		if FLAGS.task_type == "single_sentence_classification":
			name_to_features = {
				"input_ids_a":tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"label_ids":tf.FixedLenFeature([], tf.int64)
			}
		elif FLAGS.task_type == "single_sentence_multilabel_classification":
			name_to_features = {
				"input_ids_a":tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"label_ids":tf.FixedLenFeature([FLAGS.num_classes], tf.int64)
			}
		elif FLAGS.task_type == "single_sentence_multilabel_classification_bert":
			name_to_features = {
				"input_ids":tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"label_ids":tf.FixedLenFeature([FLAGS.num_classes], tf.int64)
			}
		elif FLAGS.task_type  == 'embed_sentence_classification':
			name_to_features = {
				"input_ids_a":tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"label_ids":tf.FixedLenFeature([], tf.int64)
			}
		if FLAGS.with_char == "char":
			name_to_features["input_char_ids_a"] = tf.FixedLenFeature([FLAGS.max_length], tf.int64)
			if FLAGS.task_type == "pair_sentence_classification":
				name_to_features["input_char_ids_b"] = tf.FixedLenFeature([FLAGS.max_length], tf.int64)
		if FLAGS.task_type == "pair_sentence_classification":
			name_to_features = {
				"input_ids_a":tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"label_ids":tf.FixedLenFeature([], tf.int64)
			}
			name_to_features["input_ids_b"] = tf.FixedLenFeature([FLAGS.max_length], tf.int64)

	elif FLAGS.model_type in ["textcnn_distillation", "textlstm_distillation", "dan_distillation"]:
		name_to_features = {
			"input_ids_a":tf.FixedLenFeature([FLAGS.max_length], tf.int64),
			"label_ids":tf.FixedLenFeature([], tf.int64),
			"label_ratio":tf.FixedLenFeature([], tf.float32),
			"label_probs":tf.FixedLenFeature([FLAGS.num_classes], tf.float32),
			"distillation_ratio":tf.FixedLenFeature([], tf.float32)
		}
		if FLAGS.with_char == "char":
			name_to_features["input_char_ids_a"] = tf.FixedLenFeature([FLAGS.max_length], tf.int64)
			if FLAGS.task_type == "pair_sentence_classification":
				name_to_features["input_char_ids_b"] = tf.FixedLenFeature([FLAGS.max_length], tf.int64)
		if FLAGS.task_type == "pair_sentence_classification":
			name_to_features["input_ids_b"] = tf.FixedLenFeature([FLAGS.max_length], tf.int64)
		if FLAGS.distillation in ["feature_distillation", "mdd_distillation", "rkd_distillation"]:
			name_to_features["distillation_feature"] = tf.FixedLenFeature([768], tf.float32)

	elif FLAGS.model_type in ["textcnn_distillation_adv_adaptation"]:
		name_to_features = {
			"input_ids_a":tf.FixedLenFeature([FLAGS.max_length], tf.int64),
			"label_ids":tf.FixedLenFeature([], tf.int64),
			"label_ratio":tf.FixedLenFeature([], tf.float32),
			"label_probs":tf.FixedLenFeature([FLAGS.num_classes], tf.float32),
			"distillation_ratio":tf.FixedLenFeature([], tf.float32)
		}
		if FLAGS.with_char == "char":
			name_to_features["input_char_ids_a"] = tf.FixedLenFeature([FLAGS.max_length], tf.int64)
			if FLAGS.task_type == "pair_sentence_classification":
				name_to_features["input_char_ids_b"] = tf.FixedLenFeature([FLAGS.max_length], tf.int64)
		if FLAGS.distillation in ["feature_distillation", "mdd_distillation", "rkd_distillation"]:
			name_to_features["distillation_feature"] = tf.FixedLenFeature([768], tf.float32)

		if FLAGS.distillation in ['adv_adaptation_distillation']:
			name_to_features['adv_ids'] = tf.FixedLenFeature([], tf.int64)

	elif FLAGS.model_type in ["match_pyramid", "match_pyramid_distillation"]:
		name_to_features = {
			"input_ids_a":tf.FixedLenFeature([FLAGS.max_length], tf.int64),
			"input_ids_b":tf.FixedLenFeature([FLAGS.max_length], tf.int64),
			"label_ids":tf.FixedLenFeature([], tf.int64),
			"label_ratio":tf.FixedLenFeature([], tf.float32),
			"label_probs":tf.FixedLenFeature([FLAGS.num_classes], tf.float32),
			"distillation_ratio":tf.FixedLenFeature([], tf.float32)
		}
		if FLAGS.distillation in ["feature_distillation", "mdd_distillation", "rkd_distillation"]:
			name_to_features["distillation_feature"] = tf.FixedLenFeature([768], tf.float32) 
		if FLAGS.with_char == "char":
			name_to_features["input_char_ids_a"] = tf.FixedLenFeature([FLAGS.max_length], tf.int64)
			name_to_features["input_char_ids_b"] = tf.FixedLenFeature([FLAGS.max_length], tf.int64)
	elif FLAGS.model_type in ["gpt"]:
		name_to_features = {
			"input_ids":tf.FixedLenFeature([FLAGS.max_length], tf.int64)
		}
	elif FLAGS.model_type in ["gated_cnn_seq"]:
		print(FLAGS.model_type, "===model type===", FLAGS.task_type)
		if FLAGS.task_type in ['gatedcnn_seq_lm']:
			name_to_features = {
				"input_ids_b":
						tf.FixedLenFeature([FLAGS.max_length], tf.int64)
				}

	return name_to_features

def data_interface_server(FLAGS):
	print(FLAGS.model_type, "==export==", FLAGS.task_type)
	if FLAGS.model_type in ["bert", "bert_rule", "bert_small", "albert"]:
		if FLAGS.task_type == "single_sentence_classification":

			receiver_tensors = {
				"input_ids":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids'),
				"input_mask":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_mask'),
				"segment_ids":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='segment_ids'),
				"label_ids":
						tf.placeholder(tf.int32, [None], name='label_ids'),
			}
		elif FLAGS.task_type == "single_sentence_multilabel_classification":
			receiver_tensors = {
				"input_ids":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids'),
				"input_mask":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_mask'),
				"segment_ids":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='segment_ids'),
				"label_ids":
						tf.placeholder(tf.int32, [None, FLAGS.num_classes], name='label_ids'),
			}

		elif FLAGS.task_type == "pair_sentence_classification":

			receiver_tensors = {
				"input_ids_a":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids_a'),
				"input_mask_a":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_mask_a'),
				"segment_ids_a":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='segment_ids_a'),
				"input_ids_b":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids_b'),
				"input_mask_b":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_mask_b'),
				"segment_ids_b":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='segment_ids_b'),
				"label_ids":
						tf.placeholder(tf.int32, [None], name='label_ids'),
			}
		elif FLAGS.task_type in ['bert_chid']:

			receiver_tensors = {
				"input_ids":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids'),
				"segment_ids":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='segment_ids'),
				"label_positions":
						tf.placeholder(tf.int32, [None, FLAGS.max_predictions_per_seq], name='label_positions'),
				"label_ids":
						tf.placeholder(tf.int32, [None, FLAGS.max_predictions_per_seq], name='label_ids'),
				"label_weights":
						tf.placeholder(tf.int32, [None, FLAGS.max_predictions_per_seq], name='label_weights'),

			}
		elif FLAGS.task_type in ['bert_chid_crf']:
			 name_to_features = {
				"input_ids_a":
					tf.placeholder(tf.int32, [None, FLAGS.max_length*FLAGS.max_predictions_per_seq], name='input_ids_a'),
				"segment_ids_a":
					tf.placeholder(tf.int32, [None, FLAGS.max_length*FLAGS.max_predictions_per_seq], name='segment_ids_a'),
				"input_ids_b":
					tf.placeholder(tf.int32, [None, (FLAGS.num_classes)*FLAGS.max_predictions_per_seq], name='input_ids_b'),
				"segment_ids_b":
					tf.placeholder(tf.int32, [None, (FLAGS.num_classes)*FLAGS.max_predictions_per_seq], name='segment_ids_b'),
				"label_positions":
					tf.placeholder(tf.int32, [None, FLAGS.max_predictions_per_seq], name='label_positions'),
				"label_ids":
					tf.placeholder(tf.int32, [None, FLAGS.max_predictions_per_seq], name='label_ids'),
				"label_weights":
					tf.placeholder(tf.int32, [None, FLAGS.max_predictions_per_seq], name='label_weights'),
				}
		elif FLAGS.task_type in ['bert_seq_lm']:
			name_to_features = {
				"input_ids":
					tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"input_mask":
					tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"segment_ids":
					tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"input_ori_ids":
					tf.FixedLenFeature([FLAGS.max_length], tf.int64),
				"masked_lm_positions":
					tf.FixedLenFeature([FLAGS.max_predictions_per_seq], tf.int64),
				"masked_lm_ids":
					tf.FixedLenFeature([FLAGS.max_predictions_per_seq], tf.int64),
				"masked_lm_weights":
					tf.FixedLenFeature([FLAGS.max_predictions_per_seq], tf.float32),
				"next_sentence_labels":
					tf.FixedLenFeature([], tf.int64),
			}

	elif FLAGS.model_type in ["textcnn", "textlstm", "dan"]:

		if FLAGS.task_type == "single_sentence_classification":
			receiver_tensors = {
				"input_ids_a":tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids_a'),
				"label_ids":tf.placeholder(tf.int32, [None], name='label_ids')
			}

		elif FLAGS.task_type == "single_sentence_multilabel_classification":
			receiver_tensors = {
				"input_ids_a":tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids_a'),
				"label_ids":tf.placeholder(tf.int32, [None, FLAGS.num_classes], name='label_ids')
			}
		elif FLAGS.task_type == "single_sentence_multilabel_classification_bert":
			receiver_tensors = {
				"input_ids":tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids_a'),
				"label_ids":tf.placeholder(tf.int32, [None, FLAGS.num_classes], name='label_ids')
			}
		elif FLAGS.task_type == "embed_sentence_classification":
			receiver_tensors = {
				"input_ids_a":tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids_a'),
				"label_ids":tf.placeholder(tf.int32, [None], name='label_ids')
			}

		if FLAGS.with_char == "char":
			receiver_tensors["input_char_ids_a"] = tf.placeholder(tf.int32, [None, FLAGS.char_limit, FLAGS.max_length], name='input_char_ids_a')
				
		if FLAGS.task_type == "pair_sentence_classification":
			receiver_tensors = {
				"input_ids_a":tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids_a'),
				"label_ids":tf.placeholder(tf.int32, [None], name='label_ids')
			}
			receiver_tensors["input_ids_b"] = tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids_b')
			if FLAGS.with_char == "char":
				receiver_tensors["input_char_ids_b"] = tf.placeholder(tf.int32, [None, FLAGS.char_limit, FLAGS.max_length], name='input_char_ids_b')

	elif FLAGS.model_type in ["textcnn_distillation_adv_adaptation"]:
		receiver_tensors = {
				"input_ids_a":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids_a'),
				"label_ids":
						tf.placeholder(tf.int32, [None], name='label_ids')
			}
		if FLAGS.with_char == "char":
			name_to_features["input_char_ids_a"] = tf.FixedLenFeature([FLAGS.max_length], tf.int64)
			if FLAGS.task_type == "pair_sentence_classification":
				name_to_features["input_char_ids_b"] = tf.FixedLenFeature([FLAGS.max_length], tf.int64)

		if FLAGS.distillation in ['adv_adaptation_distillation']:
			receiver_tensors['adv_ids'] = tf.placeholder(tf.int32, [None], name='adv_ids')

	elif FLAGS.model_type in ["match_pyramid"]:
		receiver_tensors = {
			"input_ids_a":tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids_a'),
			"input_ids_b":tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids_b'),
			"label_ids":tf.placeholder(tf.int32, [None], name='label_ids')
		}

		if FLAGS.with_char == "char":
			receiver_tensors["input_char_ids_a"] = tf.placeholder(tf.int32, [None, FLAGS.char_limit, FLAGS.max_length], name='input_char_ids_a')
			receiver_tensors["input_char_ids_b"] = tf.placeholder(tf.int32, [None, FLAGS.char_limit, FLAGS.max_length], name='input_char_ids_b')

	elif FLAGS.model_type in ["gpt"]:
		receiver_tensors = {
				"input_ids":
						tf.placeholder(tf.int32, [None, None], name='input_ids')
			}

	return receiver_tensors
