import tensorflow as tf
import numpy as np
import re

try:
	from .discriminator_gumbel import model_fn_builder as discriminator
	from .generator_gumbel import model_fn_builder as generator
	from .token_discriminator import discriminator_metric_train, discriminator_metric_eval, discriminator_metric_global_train
	from .token_generator import generator_metric_fn_train, generator_metric_fn_eval
	from .generator_gumbel_normal import model_fn_builder as generator_normal
	from .token_discriminator import global_gan_loss
except:
	from discriminator_gumbel import model_fn_builder as discriminator
	from generator_gumbel import model_fn_builder as generator
	from generator_gumbel_normal import model_fn_builder as generator_normal
	from token_discriminator import discriminator_metric_train, discriminator_metric_eval, discriminator_metric_global_train
	from token_generator import generator_metric_fn_train, generator_metric_fn_eval
	from token_discriminator import global_gan_loss

import tensorflow as tf
import numpy as np
from optimizer import optimizer
from optimizer import distributed_optimizer

from model_io import model_io

import tensorflow as tf
from metric import tf_metrics
from collections import OrderedDict


def get_train_op(generator_dict, discriminator_dict, optimizer_fn, opt_config,
				generator_config, discriminator_config,
				**kargs):
	if kargs.get('train_op_type', 'joint') == 'joint':
		tf.logging.info("***** original joint train op *****")
		tvars = []
		dis_loss_ratio = kargs.get('dis_loss_ratio', 1.0)
		gen_loss_ratio = kargs.get('gen_loss_ratio', 1.0)
		tf.logging.info("***** dis loss ratio: %s, gen loss ratio: %s *****", str(dis_loss_ratio), str(gen_loss_ratio))
		tvars.extend(discriminator_dict['tvars'])
		loss = dis_loss_ratio * discriminator_dict['loss']
		if kargs.get('joint_train', '1') == '1':
			tf.logging.info("****** joint generator and discriminator training *******")
			tvars.extend(generator_dict['tvars'])
			loss += gen_loss_ratio*generator_dict['loss']
		tvars = list(set(tvars))
		update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
		with tf.control_dependencies(update_ops):
			train_op = optimizer_fn.get_train_op(loss, list(set(tvars)),
							opt_config.init_lr, 
							opt_config.num_train_steps,
							**kargs)
	elif kargs.get('train_op_type', 'joint') in ['alternate', 'group']:
		if kargs.get('gen_disc_type', 'all_disc') == 'all_disc':
			gen_disc_loss = discriminator_dict['loss']
			gen_dis_loss_ratio = kargs.get('gen_dis_loss_ratio', 10.0)
			gen_loss_ratio = kargs.get('gen_loss_ratio', 1.0)
			dis_loss_ratio = kargs.get('dis_loss_ratio', 10.0)
			tf.logging.info("***** dis loss ratio: %s, gen loss ratio: %s, gen-dis loss ratio: %s *****", 
							str(dis_loss_ratio), str(gen_loss_ratio), str(gen_dis_loss_ratio))
			tf.logging.info("****** using all disc loss for updating generator *******")
		elif kargs.get('gen_disc_type', 'all_disc') == 'not_equal_disc_loss':
			gen_disc_loss = discriminator_dict['not_equal_loss_self']
			gen_dis_loss_ratio = kargs.get('gen_dis_loss_ratio', 0.1)
			gen_loss_ratio = kargs.get('gen_loss_ratio', 1.0)
			dis_loss_ratio = kargs.get('dis_loss_ratio', 10.0)
			tf.logging.info("***** dis loss ratio: %s, gen loss ratio: %s, gen-dis loss ratio: %s *****", 
							str(dis_loss_ratio), str(gen_loss_ratio), str(gen_dis_loss_ratio))
			tf.logging.info("****** using not equal loss self for updating generator *******")
		elif kargs.get('gen_disc_type', 'all_disc') == 'equal_not_equal_disc_loss':
			gen_dis_loss_ratio = kargs.get('gen_dis_loss_ratio', 0.1)
			gen_loss_ratio = kargs.get('gen_loss_ratio', 1.0)
			dis_loss_ratio = kargs.get('dis_loss_ratio', 10.0)
			tf.logging.info("***** dis loss ratio: %s, gen loss ratio: %s, gen-dis loss ratio: %s *****", 
							str(dis_loss_ratio), str(gen_loss_ratio), str(gen_dis_loss_ratio))
			tf.logging.info("****** using not equal and equal loss self for updating generator *******")
			gen_disc_loss =  discriminator_dict['not_equal_loss_self'] - discriminator_dict['equal_loss_self']
		elif kargs.get('gen_disc_type', 'all_disc') == 'equal_not_equal_disc_loss_all':
			gen_dis_loss_ratio = kargs.get('gen_dis_loss_ratio', 0.5)
			gen_loss_ratio = kargs.get('gen_loss_ratio', 0.1)
			dis_loss_ratio = kargs.get('dis_loss_ratio', 1.0)
			tf.logging.info("***** dis loss ratio: %s, gen loss ratio: %s, gen-dis loss ratio: %s *****", 
							str(dis_loss_ratio), str(gen_loss_ratio), str(gen_dis_loss_ratio))
			tf.logging.info("****** using not equal and equal loss all for updating generator *******")
			gen_disc_loss =  discriminator_dict['not_equal_loss_all'] - discriminator_dict['equal_loss_all']
		
		elif kargs.get('gen_disc_type', 'all_disc') == 'not_equal_disc_loss_all':
			gen_dis_loss_ratio = kargs.get('gen_dis_loss_ratio', 10.0)
			gen_loss_ratio = kargs.get('gen_loss_ratio', 1.0)
			dis_loss_ratio = kargs.get('dis_loss_ratio', 10.0)
			tf.logging.info("***** dis loss ratio: %s, gen loss ratio: %s, gen-dis loss ratio: %s *****", 
							str(dis_loss_ratio), str(gen_loss_ratio), str(gen_dis_loss_ratio))
			tf.logging.info("****** using not equal all for updating generator *******")
			gen_disc_loss =  discriminator_dict['not_equal_loss_all']
		else:
			gen_dis_loss_ratio = kargs.get('gen_dis_loss_ratio', 10.0)
			gen_loss_ratio = kargs.get('gen_loss_ratio', 1.0)
			dis_loss_ratio = kargs.get('dis_loss_ratio', 10.0)
			tf.logging.info("***** dis loss ratio: %s, gen loss ratio: %s, gen-dis loss ratio: %s *****", 
							str(dis_loss_ratio), str(gen_loss_ratio), str(gen_dis_loss_ratio))
			gen_disc_loss = discriminator_dict['loss']
			tf.logging.info("****** using all disc loss for updating generator *******")

		generator_loss = gen_loss_ratio * generator_dict['loss'] - gen_dis_loss_ratio * gen_disc_loss
		discriminator_loss = dis_loss_ratio * discriminator_dict['loss']
		
		if kargs.get('use_tpu', 0) == 0:
			tf.logging.info("====logging discriminator loss ====")
			tf.summary.scalar('generator_loss_adv', 
								generator_loss)

			optimizer_fn.gradient_norm_summary(generator_dict['loss'], generator_dict['tvars'], debug_grad_name="generator_grad_norm")
			optimizer_fn.gradient_norm_summary(gen_disc_loss, generator_dict['tvars'], debug_grad_name="discriminator_of_generator_grad_norm")

		loss_dict = OrderedDict(zip(['generator', 'discriminator'], [generator_loss, discriminator_loss]))
		tvars_dict = OrderedDict(zip(['generator', 'discriminator'], [generator_dict['tvars'], discriminator_dict['tvars']]))
		init_lr_dict = OrderedDict(zip(['generator', 'discriminator'], [generator_config['init_lr'], discriminator_config['init_lr']]))
		optimizer_type_dict = OrderedDict(zip(['generator', 'discriminator'], [generator_config['optimizer_type'], discriminator_config['optimizer_type']]))
		print(loss_dict, '===loss dict=====')
		if kargs.get('train_op_type', 'joint') == 'alternate':
			tf.logging.info("***** alternate train op for minmax *****")
			train_op_fn = optimizer_fn.get_alternate_train_op
		elif kargs.get('train_op_type', 'joint') == 'group':
			tf.logging.info("***** joint train op for minmax *****")
			train_op_fn = optimizer_fn.get_group_train_op

		update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
		with tf.control_dependencies(update_ops):
			train_op = train_op_fn(loss_dict, 
									tvars_dict, 
									init_lr_dict,
									optimizer_type_dict,
									opt_config.num_train_steps,
									**kargs)
	return train_op

def classifier_model_fn_builder(
						model_config_dict,
						num_labels_dict,
						init_checkpoint_dict,
						load_pretrained_dict,
						model_io_config={},
						opt_config={},
						exclude_scope_dict={},
						not_storage_params_dict={},
						target_dict={},
						**kargs):
	# graph = kargs.get('graph', None)
	# with graph.as_default():
	def model_fn(features, labels, mode, params):

		train_op_type = kargs.get('train_op_type', 'joint')
		gen_disc_type = kargs.get('gen_disc_type', 'all_disc')
		print(train_op_type, "===train op type===", gen_disc_type, "===generator loss type===")
		if kargs.get('optimization_type', 'grl') == 'grl':
			if_flip_grad = True
			train_op_type = 'joint'
		elif kargs.get('optimization_type', 'grl') == 'minmax':
			if_flip_grad = False
		generator_fn = generator(model_config_dict['generator'],
					num_labels_dict['generator'],
					init_checkpoint_dict['generator'],
					model_reuse=None,
					load_pretrained=load_pretrained_dict['generator'],
					model_io_config=model_io_config,
					opt_config=opt_config,
					exclude_scope=exclude_scope_dict.get('generator', ""),
					not_storage_params=not_storage_params_dict.get('generator', []),
					target=target_dict['generator'],
					if_flip_grad=if_flip_grad,
					mask_method="all_mask",
					**kargs)
		
		tf.logging.info("****** train_op_type:%s *******", train_op_type)
		tf.logging.info("****** optimization_type:%s *******", kargs.get('optimization_type', 'grl'))
		generator_dict = generator_fn(features, labels, mode, params)

		discriminator_fn = discriminator(model_config_dict['discriminator'],
					num_labels_dict['discriminator'],
					init_checkpoint_dict['discriminator'],
					model_reuse=None,
					load_pretrained=load_pretrained_dict['discriminator'],
					model_io_config=model_io_config,
					opt_config=opt_config,
					exclude_scope=exclude_scope_dict.get('discriminator', ""),
					not_storage_params=not_storage_params_dict.get('discriminator', []),
					target=target_dict['discriminator'],
					**kargs)

		tf.logging.info("****** true sampled_ids of discriminator *******")
		true_distriminator_features = {}
		true_distriminator_features['input_ids'] = generator_dict['sampled_input_ids']
		true_distriminator_features['input_mask'] = generator_dict['sampled_input_mask']
		true_distriminator_features['segment_ids'] = generator_dict['sampled_segment_ids']
		true_distriminator_features['input_ori_ids'] = generator_dict['sampled_input_ids']
		true_distriminator_features['next_sentence_labels'] = features['next_sentence_labels']
		true_distriminator_features['ori_input_ids'] = generator_dict['sampled_input_ids']

		true_distriminator_dict = discriminator_fn(true_distriminator_features, labels, 
													mode, params)

		fake_discriminator_features = {}
		if kargs.get('minmax_mode', 'corrupted') == 'corrupted':
			tf.logging.info("****** gumbel 3-D sampled_ids *******")
		elif kargs.get('minmax_mode', 'corrupted') == 'masked':
			fake_discriminator_features['ori_sampled_ids'] = generator_dict['output_ids']
			discriminator_features['sampled_binary_mask'] = generator_dict['sampled_binary_mask']
			tf.logging.info("****** conditioanl sampled_ids *******")
		fake_discriminator_features['input_ids'] = generator_dict['sampled_ids']
		fake_discriminator_features['input_mask'] = generator_dict['sampled_input_mask']
		fake_discriminator_features['segment_ids'] = generator_dict['sampled_segment_ids']
		fake_discriminator_features['input_ori_ids'] = generator_dict['sampled_input_ids']
		fake_discriminator_features['next_sentence_labels'] = features['next_sentence_labels']
		fake_discriminator_features['ori_input_ids'] = generator_dict['sampled_ids']
		
		fake_discriminator_dict = discriminator_fn(fake_discriminator_features, labels, mode, params)

		use_tpu = 1 if kargs.get('use_tpu', False) else 0

		output_dict = global_gan_loss(model_config_dict['discriminator'],
									true_distriminator_dict, 	
									true_distriminator_features,
									fake_discriminator_dict, 
									fake_discriminator_features,
									use_tpu=use_tpu)

		discriminator_dict = {}
		discriminator_dict['loss'] = output_dict['loss'] + 0.0 * fake_discriminator_dict['loss']
		discriminator_dict['tvars'] = fake_discriminator_dict['tvars']
		discriminator_dict['per_example_loss'] = fake_discriminator_dict['per_example_loss']
		discriminator_dict['logits'] = fake_discriminator_dict['logits']

		model_io_fn = model_io.ModelIO(model_io_config)

		seq_global_vars = model_io_fn.get_params("cls/seq_global", 
									not_storage_params=[])
		discriminator_dict['tvars'].extend(seq_global_vars)

		tvars = []

		loss = discriminator_dict['loss']

		tvars.extend(discriminator_dict['tvars'])

		if kargs.get('joint_train', '1') == '1':
			tf.logging.info("****** joint generator and discriminator training *******")
			tvars.extend(generator_dict['tvars'])
			loss += generator_dict['loss']
		tvars = list(set(tvars))

		# logging_hook = tf.train.LoggingTensorHook({ 
		# 				"generator_loss" : tf.get_collection('generator_loss'),
		# 				"discriminator_loss":tf.get_collection('discriminator_loss')},
		# 				every_n_iter=1000)

		var_checkpoint_dict_list = []
		for key in init_checkpoint_dict:
			if load_pretrained_dict[key] == "yes":
				if key == 'generator':
					tmp = {
							"tvars":generator_dict['tvars'],
							"init_checkpoint":init_checkpoint_dict['generator'],
							"exclude_scope":exclude_scope_dict[key],
							"restore_var_name":model_config_dict['generator'].get('restore_var_name', [])
					}
					if kargs.get("sharing_mode", "none") != "none":
						tmp['exclude_scope'] = ''
					var_checkpoint_dict_list.append(tmp)
				elif key == 'discriminator':
					tmp = {
						"tvars":discriminator_dict['tvars'],
						"init_checkpoint":init_checkpoint_dict['discriminator'],
						"exclude_scope":exclude_scope_dict[key],
						"restore_var_name":model_config_dict['discriminator'].get('restore_var_name', [])
					}
					var_checkpoint_dict_list.append(tmp)

		use_tpu = 1 if kargs.get('use_tpu', False) else 0
			
		if len(var_checkpoint_dict_list) >= 1:
			scaffold_fn = model_io_fn.load_multi_pretrained(var_checkpoint_dict_list,
											use_tpu=use_tpu)
		else:
			scaffold_fn = None

		if mode == tf.estimator.ModeKeys.TRAIN:

			if not kargs.get('use_tpu', False):
				metric_dict = discriminator_metric_train(discriminator_dict['per_example_loss'],
								discriminator_dict['logits'], 
							generator_dict['sampled_input_ids'], 
							generator_dict['sampled_ids'],
							generator_dict['sampled_input_mask'])
				global_metric_dict = discriminator_metric_global_train(output_dict)

				for key in global_metric_dict:
					tf.summary.scalar(key, global_metric_dict[key])

				for key in metric_dict:
					tf.summary.scalar(key, metric_dict[key])
				tf.summary.scalar("generator_loss", generator_dict['loss'])
				tf.summary.scalar("discriminator_loss", discriminator_dict['loss'])
	
			if kargs.get('use_tpu', False):
				optimizer_fn = optimizer.Optimizer(opt_config)
				use_tpu = 1
			else:
				optimizer_fn = distributed_optimizer.Optimizer(opt_config)
				use_tpu = 0

			model_io_fn.print_params(tvars, string=", trainable params")

			train_op = get_train_op(generator_dict, discriminator_dict, optimizer_fn, opt_config,
						model_config_dict['generator'], model_config_dict['discriminator'],
						use_tpu=use_tpu, train_op_type=train_op_type, gen_disc_type=gen_disc_type)
			
			# update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
			# with tf.control_dependencies(update_ops):
			# 	train_op = optimizer_fn.get_train_op(loss, list(set(tvars)),
			# 					opt_config.init_lr, 
			# 					opt_config.num_train_steps,
			# 					use_tpu=use_tpu)

			if kargs.get('use_tpu', False):
				estimator_spec = tf.contrib.tpu.TPUEstimatorSpec(
								mode=mode,
								loss=loss,
								train_op=train_op,
								scaffold_fn=scaffold_fn
								# training_hooks=[logging_hook]
								)
			else:
				estimator_spec = tf.estimator.EstimatorSpec(
								mode=mode, 
								loss=loss, 
								train_op=train_op)

			return estimator_spec

		elif mode == tf.estimator.ModeKeys.EVAL:

			if kargs.get('joint_train', '0') == '1':

				def joint_metric(masked_lm_example_loss, masked_lm_log_probs,
								masked_lm_ids, masked_lm_weights,
								next_sentence_example_loss, next_sentence_log_probs,
								next_sentence_labels,
								per_example_loss, logits,
								input_ori_ids, input_ids,
								input_mask):
					generator_metric = generator_metric_fn_eval(
										masked_lm_example_loss,
										masked_lm_log_probs,
										masked_lm_ids,
										masked_lm_weights,
										next_sentence_example_loss,
										next_sentence_log_probs,
										next_sentence_labels
										)
					discriminator_metric = discriminator_metric_eval(
							per_example_loss,
							logits, 
							input_ori_ids, 
							input_ids,
							input_mask)
					generator_metric.update(discriminator_metric)
					return generator_metric

				tpu_eval_metrics = (joint_metric, [
										generator_dict['masked_lm_example_loss'],
										generator_dict['masked_lm_log_probs'],
										generator_dict['masked_lm_ids'],
										generator_dict['masked_lm_weights'],
										generator_dict.get('next_sentence_example_loss', None),
										generator_dict.get('next_sentence_log_probs', None),
										generator_dict.get('next_sentence_labels', None),
										discriminator_dict['per_example_loss'],
										discriminator_dict['logits'], 
										generator_dict['sampled_input_ids'], 
										generator_dict['sampled_ids'],
										generator_dict['sampled_input_mask']])
				gpu_eval_metrics = joint_metric(generator_dict['masked_lm_example_loss'],
										generator_dict['masked_lm_log_probs'],
										generator_dict['masked_lm_ids'],
										generator_dict['masked_lm_weights'],
										generator_dict.get('next_sentence_example_loss', None),
										generator_dict.get('next_sentence_log_probs', None),
										generator_dict.get('next_sentence_labels', None),
										discriminator_dict['per_example_loss'],
										discriminator_dict['logits'], 
										generator_dict['sampled_input_ids'], 
										generator_dict['sampled_ids'],
										generator_dict['sampled_input_mask'])
			else:
				gpu_eval_metrics = discriminator_metric_eval(
								discriminator_dict['per_example_loss'],
								discriminator_dict['logits'], 
								generator_dict['sampled_input_ids'], 
								generator_dict['sampled_ids'],
								generator_dict['sampled_input_mask'])
				tpu_eval_metrics = (discriminator_metric_eval, [
											discriminator_dict['per_example_loss'],
											discriminator_dict['logits'], 
											generator_dict['sampled_input_ids'], 
											generator_dict['sampled_ids'],
											generator_dict['sampled_input_mask']
							])		

			if kargs.get('use_tpu', False):
				estimator_spec = tf.contrib.tpu.TPUEstimatorSpec(
							  mode=mode,
							  loss=loss,
							  eval_metrics=tpu_eval_metrics,
							  scaffold_fn=scaffold_fn)
			else:
				estimator_spec = tf.estimator.EstimatorSpec(mode=mode, 
								loss=loss,
								eval_metric_ops=gpu_eval_metrics)

			return estimator_spec
		else:
			raise NotImplementedError()

	return model_fn


