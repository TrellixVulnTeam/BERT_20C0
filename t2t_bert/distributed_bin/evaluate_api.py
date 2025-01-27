
# -*- coding: utf-8 -*-
import sys,os,json

father_path = os.path.join(os.getcwd())
print(father_path, "==father path==")

def find_bert(father_path):
	if father_path.split("/")[-1] == "BERT":
		return father_path

	output_path = ""
	for fi in os.listdir(father_path):
		if fi == "BERT":
			output_path = os.path.join(father_path, fi)
			break
		else:
			if os.path.isdir(os.path.join(father_path, fi)):
				find_bert(os.path.join(father_path, fi))
			else:
				continue
	return output_path

bert_path = find_bert(father_path)
t2t_bert_path = os.path.join(bert_path, "t2t_bert")
sys.path.extend([bert_path, t2t_bert_path])

print(sys.path)

import tensorflow as tf

from distributed_single_sentence_classification import train_eval
from distributed_multitask import train_eval as multitask_train_eval
from data_generator import tf_data_utils
# from tensorflow.contrib.distribute.python import cross_tower_ops as cross_tower_ops_lib

import tensorflow as tf
import json

flags = tf.flags

FLAGS = flags.FLAGS

# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
tf.logging.set_verbosity(tf.logging.INFO)

flags.DEFINE_string("buckets", "", "oss buckets")

flags.DEFINE_string(
	"config_file", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"init_checkpoint", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"vocab_file", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"label_id", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_integer(
	"max_length", 128,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"train_file", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"dev_file", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"model_output", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_integer(
	"epoch", 5,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_integer(
	"num_classes", 5,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_integer(
	"train_size", 1402171,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_integer(
	"batch_size", 32,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"model_type", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"if_shard", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_integer(
	"eval_size", 1000,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"opt_type", "ps_sync",
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"is_debug", "0",
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"run_type", "0",
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_integer(
	"num_gpus", 2, 
	"the required num_gpus"
	)

flags.DEFINE_string(
	"distribution_strategy", "MirroredStrategy", 
	"the required num_gpus"
	)

flags.DEFINE_string(
	"parse_type", "parse_single", 
	"the required num_gpus"
	)

flags.DEFINE_string(
	"rule_model", "normal", 
	"the required num_gpus"
	)

flags.DEFINE_string(
	"profiler", "normal", 
	"the required num_gpus"
	)

flags.DEFINE_string(
	"train_op", "adam", 
	"the required num_gpus"
	)

flags.DEFINE_string(
	"running_type", "eval", 
	"the required num_gpus"
	)

flags.DEFINE_string(
	"input_target", "a", 
	"the required num_gpus"
	)

flags.DEFINE_string(
	"load_pretrained", "no", 
	"the required num_gpus"
	)

flags.DEFINE_string(
	"w2v_path", "",
	"pretrained w2v"
	)

flags.DEFINE_string(
	"with_char", "no_char",
	"pretrained w2v"
	)

flags.DEFINE_string(
	"decay", "no",
	"pretrained w2v"
	)

flags.DEFINE_string(
	"warmup", "no",
	"pretrained w2v"
	)

flags.DEFINE_string(
	"distillation", "normal",
	"if apply distillation"
	)

flags.DEFINE_integer(
	"num_hidden_layers", 12,
	"if apply distillation"
	)

flags.DEFINE_string(
	"task_type", "single_sentence_classification",
	"if apply distillation"
	)

flags.DEFINE_string(
	"classifier", "order_classifier",
	"if apply distillation"
	)

flags.DEFINE_string(
	"output_layer", "interaction",
	"if apply distillation"
	)

flags.DEFINE_integer(
	"char_limit", 5,
	"if apply distillation"
	)

flags.DEFINE_string(
	"mode", "single_task",
	"if apply distillation"
	)

flags.DEFINE_string(
	"multi_task_type", "wsdm",
	"if apply distillation"
	)

flags.DEFINE_string(
	"multi_task_config", "wsdm",
	"if apply distillation"
	)

flags.DEFINE_string(
	"task_invariant", "no",
	"if apply distillation"
	)

flags.DEFINE_float(
	"init_lr", 5e-5,
	"if apply distillation"
	)

flags.DEFINE_string(
	"multitask_balance_type", "data_balanced",
	"if apply distillation"
	)

flags.DEFINE_integer(
	"prefetch", 0,
	"if apply distillation"
	)

flags.DEFINE_string(
	"feature_output", "feature.info",
	"if apply distillation"
	)
flags.DEFINE_integer(
	"max_predictions_per_seq", 10,
	"if apply distillation"
	)

flags.DEFINE_string(
	"ln_type", 'postln',
	"if apply distillation"
	)

flags.DEFINE_string(
	"attention_type", "normal_attention",
	"if apply distillation"
	)

flags.DEFINE_string(
	"exclude_scope", "",
	"if apply distillation"
	)

flags.DEFINE_string(
	"ues_token_type", "yes",
	"if apply distillation"
	)

flags.DEFINE_string(
	"model_scope", "bert",
	"if apply distillation"
	)

def main(_):

	print(FLAGS)
	print(tf.__version__, "==tensorflow version==")

	init_checkpoint = os.path.join(FLAGS.buckets, FLAGS.init_checkpoint)
	train_file = os.path.join(FLAGS.buckets, FLAGS.train_file)
	dev_file = os.path.join(FLAGS.buckets, FLAGS.dev_file)
	checkpoint_dir = os.path.join(FLAGS.buckets, FLAGS.model_output)

	print(init_checkpoint, train_file, dev_file, checkpoint_dir)

	sess_config = tf.ConfigProto(allow_soft_placement=True,
									log_device_placement=True)

	cluster = {'chief': ['localhost:2221'], 'worker': ['localhost:2222']}
	try:
		os.environ['TF_CONFIG'] = json.dumps({'cluster': cluster, 'task': {'type': 'evaluator', 'index': 0}})
	except:
		print("==not tf config env==")

	run_config = tf.estimator.RunConfig(
					  keep_checkpoint_max=5,
					  model_dir=checkpoint_dir, 
					  session_config=sess_config,
					  save_checkpoints_secs=None,
					  save_checkpoints_steps=None,
					  log_step_count_steps=100)

	task_index = run_config.task_id
	is_chief = run_config.is_chief
	worker_count = 1

	print("==worker_count==", worker_count, "==local_rank==", task_index, "==is is_chief==", is_chief)
	target = ""

	if FLAGS.mode == "single_task":
		train_eval_api = train_eval
	elif FLAGS.mode == "multi_task":
		train_eval_api = multitask_train_eval

	if FLAGS.run_type == "estimator":
		train_eval_api.monitored_estimator(
			FLAGS=FLAGS,
			worker_count=worker_count,
			task_index=task_index, 
			cluster=cluster, 
			is_chief=is_chief, 
			target=target,
			init_checkpoint=init_checkpoint,
			train_file=train_file,
			dev_file=dev_file,
			checkpoint_dir=checkpoint_dir,
			run_config=run_config,
			profiler=FLAGS.profiler,
			parse_type=FLAGS.parse_type,
			rule_model=FLAGS.rule_model,
			train_op=FLAGS.train_op,
			running_type="eval",
			input_target=FLAGS.input_target,
			ues_token_type=FLAGS.ues_token_type,
			attention_type=FLAGS.attention_type)
	elif FLAGS.run_type == "sess":
		result_dict = train_eval_api.monitored_sess(FLAGS=FLAGS,
			worker_count=worker_count,
			task_index=task_index, 
			cluster=cluster, 
			is_chief=is_chief, 
			target=target,
			init_checkpoint=init_checkpoint,
			train_file=train_file,
			dev_file=dev_file,
			checkpoint_dir=checkpoint_dir,
			run_config=run_config,
			profiler=FLAGS.profiler,
			parse_type=FLAGS.parse_type,
			rule_model=FLAGS.rule_model,
			train_op=FLAGS.train_op,
			running_type="eval",
			input_target=FLAGS.input_target,
			ues_token_type=FLAGS.ues_token_type,
			attention_type=FLAGS.attention_type)

		result_log_file = os.path.join(checkpoint_dir, FLAGS.feature_output)
		print(result_log_file, "==result log path==")
		# with tf.gfile.GFile(result_log_file, 'w') as f:
		# 	f.write(json.dumps(result_dict)+"\n")
		writer = tf.python_io.TFRecordWriter(result_log_file)
		try:
			for label_id, feature, prob in zip(result_dict["label_ids"], 
												result_dict["feature"],
												result_dict["prob"]):
				features = {}
				features["label_id"] = tf_data_utils.create_int_feature([label_id])
				features["feature"] = tf_data_utils.create_float_feature(feature)
				features["prob"] = tf_data_utils.create_float_feature(prob)

				tf_example = tf.train.Example(features=tf.train.Features(feature=features))
				writer.write(tf_example.SerializeToString())
			writer.close()
		except:
			print("===not legal output for writer===")

if __name__ == "__main__":
	tf.app.run()