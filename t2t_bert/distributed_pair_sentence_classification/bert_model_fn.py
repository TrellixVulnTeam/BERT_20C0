try:
	from distributed_single_sentence_classification.model_interface import model_zoo
except:
	from distributed_single_sentence_classification.model_interface import model_zoo

import tensorflow as tf
import numpy as np
from loss import loss_utils, triplet_loss_utils

from model_io import model_io
from task_module import classifier
import tensorflow as tf
from metric import tf_metrics

from optimizer import distributed_optimizer as optimizer
from model_io import model_io

def correlation(x, y):
	x = x - tf.reduce_mean(x, axis=-1, keepdims=True)
	y = y - tf.reduce_mean(y, axis=-1, keepdims=True)
	x = tf.nn.l2_normalize(x, -1)
	y = tf.nn.l2_normalize(y, -1)
	return -tf.reduce_sum(x*y, axis=-1) # higher the better

def kd(x, y):
	x_prob = tf.nn.softmax(x)
	print(x_prob.get_shape(), y.get_shape(), tf.reduce_sum(x_prob * y, axis=-1).get_shape())
	return -tf.reduce_sum(x_prob * y, axis=-1) # higher the better

def mse(x, y):
	x = x - tf.reduce_mean(x, axis=-1, keepdims=True)
	y = y - tf.reduce_mean(y, axis=-1, keepdims=True)
	return tf.reduce_sum((x-y)**2, axis=-1) # lower the better

def kd_distance(x, y, dist_type):
	if dist_type == "person":
		return correlation(x,y)
	elif dist_type == "kd":
		return kd(x, y)
	elif dist_type == "mse":
		return mse(x, y)

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
					label_lst=None,
					output_type="sess",
					**kargs):

	def model_fn(features, labels, mode):

		model_api = model_zoo(model_config)

		model_lst = []

		assert len(target.split(",")) == 2
		target_name_lst = target.split(",")
		print(target_name_lst)
		model_config.use_one_hot_embeddings = True
		for index, name in enumerate(target_name_lst):
			if index > 0:
				reuse = True
			else:
				reuse = model_reuse
			model_lst.append(model_api(model_config, features, labels,
							mode, name, reuse=reuse))

		label_ids = features["label_ids"]

		if mode == tf.estimator.ModeKeys.TRAIN:
			dropout_prob = model_config.dropout_prob
		else:
			dropout_prob = 0.0

		if model_io_config.fix_lm == True:
			scope = model_config.scope + "_finetuning"
		else:
			scope = model_config.scope

		with tf.variable_scope(scope, reuse=model_reuse):
			seq_output_lst = [model.get_pooled_output() for model in model_lst]
			if model_config.get("classifier", "order_classifier") == "order_classifier":
				[loss, 
					per_example_loss, 
					logits] = classifier.order_classifier(
								model_config, seq_output_lst, 
								num_labels, label_ids,
								dropout_prob, ratio_weight=None)
			elif model_config.get("classifier", "order_classifier") == "siamese_interaction_classifier":
				[loss, 
					per_example_loss, 
					logits] = classifier.siamese_classifier(
								model_config, seq_output_lst, 
								num_labels, label_ids,
								dropout_prob, ratio_weight=None)

		if kargs.get('apply_gp', False):
			gp_loss = loss_utils.gradient_penalty_loss(loss, model_lst[0].get_embedding_table(), 
											epsilon=1.0)
			loss += gp_loss
			tf.logging.info("****** apply gradient penalty *******")

		if mode == tf.estimator.ModeKeys.TRAIN:
			if kargs.get('distillation', 'normal') == 'distillation':
				print(kargs.get("temperature", 0.5), kargs.get("distillation_ratio", 0.5), "==distillation hyparameter==")

				# anneal_fn = anneal_strategy.AnnealStrategy(kargs.get("anneal_config", {}))

				# get teacher logits
				teacher_logit = tf.log(features["label_probs"]+1e-10)/kargs.get("temperature", 2.0) # log_softmax logits
				student_logit = tf.nn.log_softmax(logits /kargs.get("temperature", 2.0)) # log_softmax logits

				distillation_loss = kd_distance(teacher_logit, student_logit, kargs.get("distillation_distance", "kd")) 
				distillation_loss *= features["distillation_ratio"]
				distillation_loss = tf.reduce_sum(distillation_loss) / (1e-10+tf.reduce_sum(features["distillation_ratio"]))

				label_loss = tf.reduce_sum(per_example_loss * features["label_ratio"]) / (1e-10+tf.reduce_sum(features["label_ratio"]))
			
				print("==distillation loss ratio==", kargs.get("distillation_ratio", 0.9)*tf.pow(kargs.get("temperature", 2.0), 2))

				# loss = label_loss + kargs.get("distillation_ratio", 0.9)*tf.pow(kargs.get("temperature", 2.0), 2)*distillation_loss
				loss = (1-kargs.get("distillation_ratio", 0.9))*label_loss + tf.pow(kargs.get("temperature", 2.0), 2)*kargs.get("distillation_ratio", 0.9) * distillation_loss

		model_io_fn = model_io.ModelIO(model_io_config)

		params_size = model_io_fn.count_params(model_config.scope)
		print("==total params==", params_size)

		tvars = model_io_fn.get_params(model_config.scope, 
										not_storage_params=not_storage_params)
		print(tvars)
		if load_pretrained == "yes":
			model_io_fn.load_pretrained(tvars, 
										init_checkpoint,
										exclude_scope=exclude_scope)

		if mode == tf.estimator.ModeKeys.TRAIN:

			optimizer_fn = optimizer.Optimizer(opt_config)

			model_io_fn.print_params(tvars, string=", trainable params")
			update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
			with tf.control_dependencies(update_ops):

				train_op = optimizer_fn.get_train_op(loss, tvars, 
								opt_config.init_lr, 
								opt_config.num_train_steps,
								**kargs)

				model_io_fn.set_saver()

				if kargs.get("task_index", 1) == 0 and kargs.get("run_config", None):
					training_hooks = []
				elif kargs.get("task_index", 1) == 0:
					model_io_fn.get_hooks(kargs.get("checkpoint_dir", None), 
														kargs.get("num_storage_steps", 1000))

					training_hooks = model_io_fn.checkpoint_hook
				else:
					training_hooks = []

				if len(optimizer_fn.distributed_hooks) >= 1:
					training_hooks.extend(optimizer_fn.distributed_hooks)
				print(training_hooks, "==training_hooks==", "==task_index==", kargs.get("task_index", 1))

				estimator_spec = tf.estimator.EstimatorSpec(mode=mode, 
								loss=loss, train_op=train_op,
								training_hooks=training_hooks)
				if output_type == "sess":
					return {
						"train":{
										"loss":loss, 
										"logits":logits,
										"train_op":train_op
									},
						"hooks":training_hooks
					}
				elif output_type == "estimator":
					return estimator_spec

		elif mode == tf.estimator.ModeKeys.PREDICT:
			print(logits.get_shape(), "===logits shape===")
			pred_label = tf.argmax(logits, axis=-1, output_type=tf.int32)

			print(logits.get_shape(), "===logits shape===")
			pred_label = tf.argmax(logits, axis=-1, output_type=tf.int32)
			prob = tf.nn.softmax(logits)
			max_prob = tf.reduce_max(prob, axis=-1)
			
			
			estimator_spec = tf.estimator.EstimatorSpec(
									mode=mode,
									predictions={
												'pred_label':pred_label,
												"max_prob":max_prob,
												"prob":prob
									},
									export_outputs={
										"output":tf.estimator.export.PredictOutput(
													{
														'pred_label':pred_label,
														"max_prob":max_prob,
														"prob":prob
													}
												)
									}
						)
			return estimator_spec

		elif mode == tf.estimator.ModeKeys.EVAL:
			def metric_fn(per_example_loss,
						logits, 
						label_ids):
				"""Computes the loss and accuracy of the model."""
				sentence_log_probs = tf.reshape(
					logits, [-1, logits.shape[-1]])
				sentence_predictions = tf.argmax(
					logits, axis=-1, output_type=tf.int32)
				sentence_labels = tf.reshape(label_ids, [-1])
				sentence_accuracy = tf.metrics.accuracy(
					labels=label_ids, predictions=sentence_predictions)
				sentence_mean_loss = tf.metrics.mean(
					values=per_example_loss)
				sentence_f = tf_metrics.f1(label_ids, 
										sentence_predictions, 
										num_labels, 
										label_lst, average="macro")

				eval_metric_ops = {
									"f1": sentence_f,
									"acc":sentence_accuracy
								}

				return eval_metric_ops

			eval_metric_ops = metric_fn( 
							per_example_loss,
							logits, 
							label_ids)
			
			estimator_spec = tf.estimator.EstimatorSpec(mode=mode, 
								loss=loss,
								eval_metric_ops=eval_metric_ops)

			if output_type == "sess":
				return {
					"eval":{
							"per_example_loss":per_example_loss,
							"logits":logits,
							"loss":tf.reduce_mean(per_example_loss),
							"feature":(seq_output_lst[0]+seq_output_lst[1])/2
						}
				}
			elif output_type == "estimator":
				return estimator_spec
		else:
			raise NotImplementedError()
	return model_fn


