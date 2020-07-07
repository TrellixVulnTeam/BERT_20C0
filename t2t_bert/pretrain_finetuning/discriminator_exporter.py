import tensorflow as tf
import numpy as np

from task_module import pretrain, classifier, pretrain_albert
import tensorflow as tf

try:
	from distributed_single_sentence_classification.model_interface import model_zoo
except:
	from distributed_single_sentence_classification.model_interface import model_zoo

from pretrain_finetuning.token_discriminator import classifier
from model_io import model_io

def model_fn_builder(
					model_config,
					num_labels,
					init_checkpoint,
					model_reuse=None,
					load_pretrained=True,
					model_io_config={},
					opt_config={},
					exclude_scope="",
					not_storage_params=[],
					target="a",
					**kargs):

	def model_fn(features, labels, mode, params):

		model_api = model_zoo(model_config)

		model = model_api(model_config, features, labels,
							mode, target, reuse=tf.AUTO_REUSE,
							**kargs)

		if mode == tf.estimator.ModeKeys.TRAIN:
			dropout_prob = model_config.dropout_prob
		else:
			dropout_prob = 0.0

		if model_io_config.fix_lm == True:
			scope = model_config.scope + "_finetuning"
		else:
			scope = model_config.scope

		(_, 
		 _, 
		 nsp_log_prob) = pretrain.get_next_sentence_output(model_config,
										model.get_pooled_output(),
										features['next_sentence_labels'],
										reuse=tf.AUTO_REUSE)

		with tf.variable_scope('discriminator_predictions', reuse=tf.AUTO_REUSE):
			(_, 
			logits, 
			_) = classifier(model_config, 
									model.get_sequence_output(),
									features['input_ori_ids'],
									features['input_ids'],
									features['input_mask'],
									2,
									dropout_prob)
									# ,
									# loss='focal_loss')

		# loss += 0.0 * nsp_loss

		model_io_fn = model_io.ModelIO(model_io_config)

		pretrained_tvars = model_io_fn.get_params(model_config.scope, 
										not_storage_params=not_storage_params)
		# lm_seq_prediction_tvars = model_io_fn.get_params("discriminator_predictions", 
		# 							not_storage_params=not_storage_params)
		# lm_pretrain_tvars = model_io_fn.get_params("cls/seq_relationship", 
		# 							not_storage_params=not_storage_params)

		# pretrained_tvars.extend(lm_seq_prediction_tvars)
		# pretrained_tvars.extend(lm_pretrain_tvars)
		tvars = pretrained_tvars

		print('==discriminator parameters==', tvars)

		if load_pretrained == "yes":
			use_tpu = 1 if kargs.get('use_tpu', False) else 0
			scaffold_fn = model_io_fn.load_pretrained(tvars, 
											init_checkpoint,
											exclude_scope=exclude_scope,
											use_tpu=use_tpu)
		else:
			scaffold_fn = None
		
		return_dict = {
					"logits":logits,
					"tvars":tvars
				}
		return return_dict
	return model_fn