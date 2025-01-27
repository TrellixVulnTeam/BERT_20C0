# -*- coding: utf-8 -*-
import sys,os

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

from distributed_single_sentence_classification import hvd_train_eval
from distributed_multitask import hvd_train_eval as multitask_hvd_train_eval

import tensorflow as tf

flags = tf.flags

FLAGS = flags.FLAGS

# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
tf.logging.set_verbosity(tf.logging.ERROR)

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

flags.DEFINE_string(
	"distribution_strategy", "ParameterServerStrategy",
	"distribution strategy"
	)

flags.DEFINE_string(
	"rule_model", "normal",
	"distribution strategy"
	)

flags.DEFINE_string(
	"parse_type", "parse_single", 
	"the required num_gpus"
	)

flags.DEFINE_string(
	"profiler", "normal", 
	"the required num_gpus"
	)


flags.DEFINE_string(
	"train_op", "adam_weight_decay_exclude", 
	"the required num_gpus"
	)

flags.DEFINE_integer(
	"num_gpus", 4, 
	"the required num_gpus"
	)

flags.DEFINE_string(
	"running_type", "train", 
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
	"input_target", "", 
	"the required num_gpus"
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

flags.DEFINE_float(
	"temperature", 2.0,
	"if apply distillation"
	)

flags.DEFINE_float(
	"distillation_ratio", 1.0,
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

def main(_):

	print(FLAGS)
	print(tf.__version__, "==tensorflow version==")

	init_checkpoint = os.path.join(FLAGS.buckets, FLAGS.init_checkpoint)
	train_file = os.path.join(FLAGS.buckets, FLAGS.train_file)
	dev_file = os.path.join(FLAGS.buckets, FLAGS.dev_file)
	checkpoint_dir = os.path.join(FLAGS.buckets, FLAGS.model_output)

	print(init_checkpoint, train_file, dev_file, checkpoint_dir)

	worker_count = 1
	task_index = 0

	is_chief = task_index == 0

	print("==worker_count==", worker_count, "==local_rank==", task_index, "==is is_chief==", is_chief)
	cluster = ""
	target = ""

	# FLAGS.config_file = os.path.join(FLAGS.buckets, FLAGS.config_file)
	FLAGS.label_id = os.path.join(FLAGS.buckets, FLAGS.label_id)

	if FLAGS.mode == "single_task":
		train_eval_api = hvd_train_eval
	elif FLAGS.mode == "multi_task":
		train_eval_api = multitask_hvd_train_eval
	
	if FLAGS.run_type == "sess":
		train_eval_api.monitored_sess(
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
			distribution_strategy=FLAGS.distribution_strategy,
			rule_model=FLAGS.rule_model,
			parse_type=FLAGS.parse_type,
			train_op=FLAGS.train_op,
			running_type=FLAGS.running_type,
			input_target=FLAGS.input_target,
			decay=FLAGS.decay,
			warmup=FLAGS.warmup,
			distillation=FLAGS.distillation,
			temperature=FLAGS.temperature,
			distillation_ratio=FLAGS.distillation_ratio)

	elif FLAGS.run_type == "estimator":
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
			distribution_strategy=FLAGS.distribution_strategy,
			rule_model=FLAGS.rule_model,
			parse_type=FLAGS.parse_type,
			train_op=FLAGS.train_op,
			running_type=FLAGS.running_type,
			input_target=FLAGS.input_target,
			decay=FLAGS.decay,
			warmup=FLAGS.warmup,
			distillation=FLAGS.distillation,
			temperature=FLAGS.temperature,
			distillation_ratio=FLAGS.distillation_ratio)

if __name__ == "__main__":
	tf.app.run()