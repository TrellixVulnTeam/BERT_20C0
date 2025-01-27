# -*- coding: utf-8 -*-
import tensorflow as tf
from collections import OrderedDict

from optimizer import distributed_optimizer as optimizer
from data_generator import distributed_tf_data_utils as tf_data_utils

try:
	from .model_data_interface import data_interface
	from distributed_single_sentence_classification.model_interface import model_config_parser
except:
	from model_data_interface import data_interface
	from distributed_single_sentence_classification.model_interface import model_config_parser

try:
	from .multitask_model_fn import multitask_model_fn
except:
	from multitask_model_fn import multitask_model_fn

import numpy as np
import tensorflow as tf
from bunch import Bunch
from model_io import model_io
import json, os

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report

try:
	import paisoar as pai
except Exception as e:
	pai = None

try:
	import horovod.tensorflow as hvd
except Exception as e:
	hvd = None

try:
	import _pickle as pkl
except Exception as e:
	pkl = None

import time

def eval_fn(FLAGS,
				worker_count, 
				task_index, 
				is_chief, 
				target,
				init_checkpoint,
				train_file,
				dev_file,
				checkpoint_dir,
				is_debug,
				**kargs):

	graph = tf.Graph()
	with graph.as_default():
		import json

		# config = model_config_parser(FLAGS)
		
		if FLAGS.if_shard == "0":
			train_size = FLAGS.train_size
			epoch = int(FLAGS.epoch / worker_count)
		elif FLAGS.if_shard == "1":
			train_size = int(FLAGS.train_size/worker_count)
			epoch = FLAGS.epoch
		else:
			train_size = int(FLAGS.train_size/worker_count)
			epoch = FLAGS.epoch

		multi_task_config = Bunch(json.load(tf.gfile.Open(FLAGS.multi_task_config)))

		num_train_steps = int(
			train_size / FLAGS.batch_size * epoch)
		num_warmup_steps = int(num_train_steps * 0.1)

		num_storage_steps = int(train_size / FLAGS.batch_size)

		num_eval_steps = int(FLAGS.eval_size / FLAGS.batch_size)

		if is_debug == "0":
			num_storage_steps = 190
			num_eval_steps = 100
			num_train_steps = 200
		print("num_train_steps {}, num_eval_steps {}, num_storage_steps {}".format(num_train_steps, num_eval_steps, num_storage_steps))

		print(" model type {}".format(FLAGS.model_type))

		print(num_train_steps, num_warmup_steps, "=============")
		
		opt_config = Bunch({"init_lr":kargs.get("init_lr", 1e-5)/worker_count, 
							"num_train_steps":num_train_steps,
							"num_warmup_steps":num_warmup_steps,
							"worker_count":worker_count,
							"opt_type":FLAGS.opt_type,
							"is_chief":is_chief,
							"train_op":kargs.get("train_op", "adam"),
							"decay":kargs.get("decay", "no"),
							"warmup":kargs.get("warmup", "no"),
							"grad_clip":kargs.get("grad_clip", "global_norm"),
							"clip_norm":kargs.get("clip_norm", 1.0)})

		anneal_config = Bunch({
					"initial_value":1.0,
					"num_train_steps":num_train_steps
			})

		model_io_config = Bunch({"fix_lm":False})

		if FLAGS.opt_type == "hvd" and hvd:
			checkpoint_dir = checkpoint_dir if task_index == 0 else None
		else:
			checkpoint_dir = checkpoint_dir
		print("==checkpoint_dir==", checkpoint_dir, is_chief)

		model_config_dict = {}
		num_labels_dict = {}
		init_checkpoint_dict = {}
		load_pretrained_dict = {}
		exclude_scope_dict = {}
		not_storage_params_dict = {}
		target_dict = {}
		task_type_dict = {}
		model_type_lst = []
		label_dict = {}

		eval_model_fn = {}

		for task_type in FLAGS.multi_task_type.split(","):
			eval_task_type_dict = {}
			model_config_dict[task_type] = model_config_parser(Bunch(multi_task_config[task_type]))
			num_labels_dict[task_type] = multi_task_config[task_type]["num_labels"]
			init_checkpoint_dict[task_type] = os.path.join(FLAGS.buckets, multi_task_config[task_type]["init_checkpoint"])
			print(init_checkpoint_dict[task_type], task_type, "===", os.path.join(FLAGS.buckets, multi_task_config[task_type]["init_checkpoint"]))
			load_pretrained_dict[task_type] = multi_task_config[task_type]["load_pretrained"]
			exclude_scope_dict[task_type] = multi_task_config[task_type]["exclude_scope"]
			not_storage_params_dict[task_type] = multi_task_config[task_type]["not_storage_params"]
			target_dict[task_type] = multi_task_config[task_type]["target"]
			eval_task_type_dict[task_type] = multi_task_config[task_type]["task_type"]
			label_dict[task_type] = json.load(tf.gfile.Open(os.path.join(FLAGS.buckets,
												multi_task_config[task_type]["label_id"])))

			eval_model_fn[task_type] = multitask_model_fn(model_config_dict, num_labels_dict,
											eval_task_type_dict,
											init_checkpoint_dict,
											load_pretrained_dict=load_pretrained_dict,
											opt_config=opt_config,
											model_io_config=model_io_config,
											exclude_scope_dict=exclude_scope_dict,
											not_storage_params_dict=not_storage_params_dict,
											target_dict=target_dict,
											output_type="sess",
											checkpoint_dir=checkpoint_dir,
											num_storage_steps=num_storage_steps,
											anneal_config=anneal_config,
											task_layer_reuse=False,
											model_type_lst=model_type_lst,
											**kargs)

		print(init_checkpoint_dict, "==init_checkpoint==")

		print("==succeeded in building model==")
		
		def eval_metric_fn(features, eval_op_dict, task_type):
			logits = eval_op_dict["logits"][task_type]
			print(logits.get_shape(), "===logits shape===")
			pred_label = tf.argmax(logits, axis=-1, output_type=tf.int32)
			prob = tf.nn.softmax(logits)
			accuracy = correct = tf.equal(
				tf.cast(pred_label, tf.int32),
				tf.cast(features["{}_label_ids".format(task_type)], tf.int32)
			)
			accuracy = tf.reduce_mean(tf.cast(correct, tf.float32))

			return {"accuracy":accuracy, 
					"loss":eval_op_dict["loss"][task_type], 
					"pred_label":pred_label, 
					"label_ids":features["{}_label_ids".format(task_type)]}
		
		name_to_features = data_interface(FLAGS, multi_task_config, FLAGS.multi_task_type.split(","))

		def _decode_record(record, name_to_features):
			"""Decodes a record to a TensorFlow example.
			"""
			example = tf.parse_single_example(record, name_to_features)

			# tf.Example only supports tf.int64, but the TPU only supports tf.int32.
			# So cast all int64 to int32.
			for name in list(example.keys()):
				t = example[name]
				if t.dtype == tf.int64:
					t = tf.to_int32(t)
				example[name] = t

			return example

		def _decode_batch_record(record, name_to_features):
			example = tf.parse_example(record, name_to_features)
			return example

		params = Bunch({})
		params.epoch = 0
		params.batch_size = FLAGS.batch_size

		if kargs.get("parse_type", "parse_single") == "parse_single":

			eval_features_dict = {}
			for task_type in FLAGS.multi_task_type.split(","):
				name_to_features = data_interface(FLAGS, {task_type:multi_task_config[task_type]}, [task_type])
				eval_features_dict[task_type] = tf_data_utils.eval_input_fn(
				 						multi_task_config[task_type]["dev_result_file"],
										_decode_record, name_to_features, params, if_shard=FLAGS.if_shard,
										worker_count=worker_count,
										task_index=task_index)

		elif kargs.get("parse_type", "parse_single") == "parse_batch":

			eval_features_dict = {}
			for task_type in FLAGS.multi_task_type.split(","):
				name_to_features = data_interface(FLAGS, {task_type:multi_task_config[task_type]}, [task_type])

				dev_file_path = os.path.join(FLAGS.buckets, multi_task_config[task_type]["test_result_file"])
				eval_features_dict[task_type] = tf_data_utils.eval_batch_input_fn(
				 						dev_file_path,
										_decode_batch_record, 
										name_to_features, 
										params, 
										if_shard=FLAGS.if_shard,
										worker_count=worker_count,
										task_index=task_index)

		eval_dict = {}
		for task_type in eval_features_dict:
			eval_features = eval_features_dict[task_type]
			eval_op_dict = eval_model_fn[task_type](eval_features, [], tf.estimator.ModeKeys.EVAL)
			eval_dict_tmp = eval_metric_fn(eval_features, eval_op_dict["eval"], task_type)
			eval_dict[task_type] = eval_dict_tmp
		print(eval_dict)

		print("==succeeded in building data and model==")

		def task_eval(eval_dict, sess, eval_total_dict):
			eval_result = sess.run(eval_dict)
			for key in eval_result:
				if key not in eval_total_dict:
					if key in ["pred_label", "label_ids"]:
						eval_total_dict[key] = []
						eval_total_dict[key].extend(eval_result[key])
					if key in ["accuracy", "loss"]:
						eval_total_dict[key] = 0.0
						eval_total_dict[key] += eval_result[key]
				else:
					if key in ["pred_label", "label_ids"]:
						eval_total_dict[key].extend(eval_result[key])
					if key in ["accuracy", "loss"]:
						eval_total_dict[key] += eval_result[key]

		def task_metric(eval_dict, label_dict, eval_total_dict):
			label_id = eval_dict["label_ids"]
			pred_label = eval_dict["pred_label"]

			label_dict_id = sorted(list(label_dict["id2label"].keys()))

			print(len(label_id), len(pred_label), len(set(label_id)))

			accuracy = accuracy_score(label_id, pred_label)
			print("==accuracy==", accuracy)
			if len(label_dict["id2label"]) < 10:
				result = classification_report(label_id, pred_label, 
										target_names=[label_dict["id2label"][key] for key in label_dict_id],
										digits=4)
				print(result, task_index)
				eval_total_dict["classification_report"] = result
				print("==classification report==")

		def eval_fn(eval_dict, sess):
			i = 0
			total_accuracy = 0
			eval_total_dict = {}
			for task_type in eval_dict:
				eval_total_dict[task_type] = {}
			while True:
				try:
					for task_type in eval_dict:
						task_eval(
									eval_dict[task_type],
									sess,
									eval_total_dict[task_type]
						)
					i += 1
				except tf.errors.OutOfRangeError:
					print("End of dataset")
					break

			for task_type in eval_total_dict:
				task_metric(eval_total_dict[task_type], 
							label_dict[task_type], 
							eval_total_dict[task_type])
			return eval_total_dict

		print("start evaluating")
		sess_config = tf.ConfigProto(allow_soft_placement=False,
									log_device_placement=False)

		sess = tf.Session(config=sess_config)
		init_op = tf.group(tf.global_variables_initializer(), 
					tf.local_variables_initializer())

		sess.run(init_op)
						
		print("==begin to train and eval==")
		start_time = time.time()
		eval_finial_dict = eval_fn(eval_dict, sess)
		end_time = time.time()
		print("==forward time==", end_time - start_time)
		return eval_finial_dict


