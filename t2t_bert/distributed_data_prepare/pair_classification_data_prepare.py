import sys,os,json

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

import numpy as np
import tensorflow as tf
from bunch import Bunch
from data_generator import tokenization
import json

from example import feature_writer, write_to_tfrecords
from example import classifier_processor
from data_generator import vocab_filter

flags = tf.flags

FLAGS = flags.FLAGS

tf.logging.set_verbosity(tf.logging.INFO)

flags.DEFINE_string("buckets", "", "oss buckets")

## Required parameters
flags.DEFINE_string(
	"train_file", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"test_file", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"dev_file", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"train_result_file", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"test_result_file", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"dev_result_file", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"vocab_file", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"label_id", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_bool(
	"lower_case", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_integer(
	"max_length", None,
	"Input TF example files (can be a glob or comma separated).")

flags.DEFINE_string(
	"if_rule", "rule",
	"if apply rule detector"
	)

flags.DEFINE_string(
	"rule_word_path", "",
	"if apply rule detector"
	)

flags.DEFINE_string(
	"rule_word_dict", "",
	"if apply rule detector"
	)

flags.DEFINE_string(
	"rule_label_dict", "",
	"if apply rule detector"
	)

flags.DEFINE_string(
	"with_char", "char",
	"if apply rule detector"
	)

flags.DEFINE_integer(
	"char_len", 10,
	"if apply rule detector"
	)

flags.DEFINE_string(
	"config", "",
	"if apply rule detector"
	)

flags.DEFINE_integer(
	"predefined_vocab_size", 10000,
	"if apply rule detector"
	)

flags.DEFINE_string(
	"corpus_vocab_path", "",
	"if apply rule detector"
	)

flags.DEFINE_string(
	"data_type", "",
	"if apply rule detector"
	)

def main(_):

	tokenizer = tokenization.Jieba_CHAR(
		config=FLAGS.config)

	# with tf.gfile.Open(FLAGS.vocab_file, "r") as f:
	# 	vocab_lst = []
	# 	for line in f:
	# 		vocab_lst.append(line.strip())

	vocab_path = os.path.join(FLAGS.buckets, FLAGS.vocab_file)
	train_file = os.path.join(FLAGS.buckets, FLAGS.train_file)
	test_file = os.path.join(FLAGS.buckets, FLAGS.test_file)
	dev_file = os.path.join(FLAGS.buckets, FLAGS.dev_file)

	train_result_file = os.path.join(FLAGS.buckets, FLAGS.train_result_file)
	test_result_file = os.path.join(FLAGS.buckets, FLAGS.test_result_file)
	dev_result_file = os.path.join(FLAGS.buckets, FLAGS.dev_result_file)

	corpus_vocab_path = os.path.join(FLAGS.buckets, FLAGS.corpus_vocab_path)

	print(FLAGS.with_char)
	with tf.gfile.Open(vocab_path, "r") as f:
		lines = f.read().splitlines()
		vocab_lst = []
		for line in lines:
			vocab_lst.append(line)
		print(len(vocab_lst))

	tokenizer.load_vocab(vocab_lst)

	print("==not apply rule==")
	if FLAGS.data_type == "lcqmc":
		classifier_data_api = classifier_processor.LCQMCProcessor()
	classifier_data_api.get_labels(FLAGS.label_id)

	train_examples = classifier_data_api.get_train_examples(train_file,
										is_shuffle=True)

	vocab_filter.vocab_filter(train_examples, vocab_lst, 
							tokenizer, FLAGS.predefined_vocab_size, 
							corpus_vocab_path)

	tokenizer_corpus = tokenization.Jieba_CHAR(
		config=FLAGS.config)

	with tf.gfile.Open(corpus_vocab_path, "r") as f:
		lines = f.read().splitlines()
		vocab_lst = []
		for line in lines:
			vocab_lst.append(line)
		print(len(vocab_lst))

	tokenizer_corpus.load_vocab(vocab_lst)

	write_to_tfrecords.convert_distillation_classifier_examples_to_features(train_examples,
															classifier_data_api.label2id,
															FLAGS.max_length,
															tokenizer_corpus,
															train_result_file,
															FLAGS.with_char,
															FLAGS.char_len)

	test_examples = classifier_data_api.get_train_examples(test_file,
										is_shuffle=False)
	write_to_tfrecords.convert_distillation_classifier_examples_to_features(test_examples,
															classifier_data_api.label2id,
															FLAGS.max_length,
															tokenizer_corpus,
															test_result_file,
															FLAGS.with_char,
															FLAGS.char_len)

	dev_examples = classifier_data_api.get_train_examples(dev_file,
										is_shuffle=False)
	write_to_tfrecords.convert_distillation_classifier_examples_to_features(dev_examples,
															classifier_data_api.label2id,
															FLAGS.max_length,
															tokenizer_corpus,
															dev_result_file,
															FLAGS.with_char,
															FLAGS.char_len)

if __name__ == "__main__":
	tf.app.run()

