
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re
import tensorflow as tf

class AdamWeightDecayOptimizer(tf.train.Optimizer):
	"""A basic Adam optimizer that includes "correct" L2 weight decay."""

	def __init__(self,
							 learning_rate,
							 weight_decay_rate=0.0,
							 beta_1=0.9,
							 beta_2=0.999,
							 epsilon=1e-6,
							 exclude_from_weight_decay=None,
							 include_in_weight_decay=["r_s_bias", "r_r_bias", "r_w_bias"],
							 name="AdamWeightDecayOptimizer"):
		"""Constructs a AdamWeightDecayOptimizer."""
		super(AdamWeightDecayOptimizer, self).__init__(False, name)

		self.learning_rate = learning_rate
		self.weight_decay_rate = weight_decay_rate
		self.beta_1 = beta_1
		self.beta_2 = beta_2
		self.epsilon = epsilon
		self.exclude_from_weight_decay = exclude_from_weight_decay
		self.include_in_weight_decay = include_in_weight_decay

	def apply_gradients(self, grads_and_vars, global_step=None, name=None):
		"""See base class."""
		assignments = []
		for (grad, param) in grads_and_vars:
			if grad is None or param is None:
				continue

			param_name = self._get_variable_name(param.name)
			with tf.variable_scope(param_name, reuse=tf.AUTO_REUSE):
				m = tf.get_variable(
						name=param_name + "/adam_m",
						shape=param.shape.as_list(),
						dtype=tf.float32,
						trainable=False,
						initializer=tf.zeros_initializer())
				v = tf.get_variable(
						name=param_name + "/adam_v",
						shape=param.shape.as_list(),
						dtype=tf.float32,
						trainable=False,
						initializer=tf.zeros_initializer())

			# Standard Adam update.
			next_m = (
					tf.multiply(self.beta_1, m) + tf.multiply(1.0 - self.beta_1, grad))
			next_v = (
					tf.multiply(self.beta_2, v) + tf.multiply(1.0 - self.beta_2,
																										tf.square(grad)))

			update = next_m / (tf.sqrt(next_v) + self.epsilon)

			# Just adding the square of the weights to the loss function is *not*
			# the correct way of using L2 regularization/weight decay with Adam,
			# since that will interact with the m and v parameters in strange ways.
			#
			# Instead we want ot decay the weights in a manner that doesn't interact
			# with the m/v parameters. This is equivalent to adding the square
			# of the weights to the loss with plain (non-momentum) SGD.
			if self._do_use_weight_decay(param_name):
				update += self.weight_decay_rate * param

			# Adam bias correction
			if self.bias_correction:
				global_step_float = tf.cast(global_step, update.dtype)
				bias_correction1 = 1.0 - self.beta_1 ** (global_step_float + 1)
				bias_correction2 = 1.0 - self.beta_2 ** (global_step_float + 1)
				learning_rate = (self.learning_rate * tf.sqrt(bias_correction2)
												 / bias_correction1)
			else:
				learning_rate = self.learning_rate

			update_with_lr = learning_rate * update

			next_param = param - update_with_lr

			assignments.extend(
					[param.assign(next_param),
					 m.assign(next_m),
					 v.assign(next_v)])
		return tf.group(*assignments, name=name)

	# def _do_use_weight_decay(self, param_name):
	# 	"""Whether to use L2 weight decay for `param_name`."""
	# 	if not self.weight_decay_rate:
	# 		return False
	# 	if self.exclude_from_weight_decay:
	# 		for r in self.exclude_from_weight_decay:
	# 			if re.search(r, param_name) is not None:
	# 				return False
	# 	return True

	def _do_use_weight_decay(self, param_name):
		"""Whether to use L2 weight decay for `param_name`."""
		if not self.weight_decay_rate:
			return False

		for r in self.include_in_weight_decay:
			if re.search(r, param_name) is not None:
				tf.logging.info("Include %s in weight decay", param_name)
				return True

		if self.exclude_from_weight_decay:
			for r in self.exclude_from_weight_decay:
				if re.search(r, param_name) is not None:
					tf.logging.info("Adam WD excludes %s", param_name)
					return False
		return True

	def _get_variable_name(self, param_name):
		"""Get the variable name from the tensor name."""
		m = re.match("^(.*):\\d+$", param_name)
		if m is not None:
			param_name = m.group(1)
		return param_name

def add_grad_summaries(grads_and_vars):
	grad_summaries = []
	for g, v in grads_and_vars:
		if g is not None:
			grad_hist_summary = tf.summary.histogram("{}/grad/hist".format(v.name), g)
			sparsity_summary = tf.summary.scalar("{}/grad/sparsity".format(v.name), tf.nn.zero_fraction(g))
			grad_summaries.append(grad_hist_summary)
			grad_summaries.append(sparsity_summary)

	grad_summaries_merged = tf.summary.merge(grad_summaries)
	return grad_summaries_merged