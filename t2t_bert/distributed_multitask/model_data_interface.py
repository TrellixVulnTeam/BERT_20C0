import tensorflow as tf

def task_interface(name_to_features, task_type_dict):
	for task_type in task_type_dict:
		if task_type_dict[task_type] == "cls_task":
			name_to_features["{}_label_ids".format(task_type)] = tf.FixedLenFeature([], tf.int64)
			name_to_features["{}_mask".format(task_type)] = tf.FixedLenFeature([], tf.int64)
	return name_to_features

def data_interface(FLAGS, task_type_dict):
		
	name_to_features = {
			"input_ids":
					tf.FixedLenFeature([FLAGS.max_length], tf.int64),
			"input_mask":
					tf.FixedLenFeature([FLAGS.max_length], tf.int64),
			"segment_ids":
					tf.FixedLenFeature([FLAGS.max_length], tf.int64)
	}
	
	task_interface(name_to_features, task_type, task_type_dict)

	return name_to_features

def data_interface_server(FLAGS):
	if FLAGS.model_type in ["bert", "bert_rule", "bert_small"]:
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

	elif FLAGS.model_type in ["textcnn", "textlstm"]:
		receiver_tensors = {
				"input_ids_a":
						tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids_a'),
				"label_ids":
						tf.placeholder(tf.int32, [None], name='label_ids')
			}

		if FLAGS.with_char == "char":
			receiver_tensors["input_char_ids_a"] = tf.placeholder(tf.int32, [None, FLAGS.char_limit, FLAGS.max_length], name='input_char_ids_a')
				
		if FLAGS.task_type == "pair_sentence_classification":
			receiver_tensors["input_ids_b"] = tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids_b')
			if FLAGS.with_char == "char":
				receiver_tensors["input_char_ids_b"] = tf.placeholder(tf.int32, [None, FLAGS.char_limit, FLAGS.max_length], name='input_char_ids_b')

	elif FLAGS.model_type in ["match_pyramid"]:
		receiver_tensors = {
			"input_ids_a":tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids_a'),
			"input_ids_b":tf.placeholder(tf.int32, [None, FLAGS.max_length], name='input_ids_b'),
			"label_ids":tf.placeholder(tf.int32, [None], name='label_ids')
		}

		if FLAGS.with_char == "char":
			receiver_tensors["input_char_ids_a"] = tf.placeholder(tf.int32, [None, FLAGS.char_limit, FLAGS.max_length], name='input_char_ids_a')
			receiver_tensors["input_char_ids_b"] = tf.placeholder(tf.int32, [None, FLAGS.char_limit, FLAGS.max_length], name='input_char_ids_b')

	return receiver_tensors