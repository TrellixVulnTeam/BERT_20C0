try:
	from .model_fn import model_fn_builder
	from .model_distillation_fn import model_fn_builder as model_distillation_builder_fn
	from distributed_pair_sentence_classification.bert_model_fn import model_fn_builder as bert_nli_builder_fn
	from distributed_pair_sentence_classification.interaction_model_fn import model_fn_builder as interaction_builder_fn
	from distributed_pair_sentence_classification.interaction_distillation_model_fn import model_fn_builder as interaction_distillation_builder_fn
	from .embed_model_fn import model_fn_builder as embed_model_fn_builder
	from .model_feature_distillation_fn import model_fn_builder as feature_distillation_fn_builder
	from .model_mdd_distillation import model_fn_builder as mdd_distillation_fn_builder
	from .model_relation_distillation import model_fn_builder as rkd_distillation_fn_builder
	from distributed_pair_sentence_classification.interaction_rkd_distillation_model_fn import model_fn_builder as interaction_rkd_distillation
	# from pretrain_finetuning.classifier_fn_estimator import classifier_model_fn_builder as bert_pretrain_finetuning
	
	from pretrain_finetuning.classifier_fn_tpu_estimator import classifier_model_fn_builder as bert_pretrain_finetuning

	from .model_distillation_adv_adaptation import model_fn_builder as model_distillation_adv_adaptation_build_fn 
	from distributed_gpt.model_fn import model_fn_builder as gpt_lm_builder_fn
	from chid_nlpcc2019.model_fn import model_fn_builder as chid_model_fn_builder
	from chid_nlpcc2019.model_fn_crf import model_fn_builder as chid_crf_model_fn_builder
	from pretrain_finetuning.classifier_fn_tpu_bert_seq_estimator import classifier_model_fn_builder as bert_seq_model_fn_builder
	from pretrain_finetuning.classifier_fn_tpu_gatedcnn_estimator import classifier_model_fn_builder as gatedcnn_model_fn_builder
except:
	from model_fn import model_fn_builder
	from model_distillation_fn import model_fn_builder as model_distillation_builder_fn
	from distributed_pair_sentence_classification.bert_model_fn import model_fn_builder as bert_nli_builder_fn
	from distributed_pair_sentence_classification.interaction_model_fn import model_fn_builder as interaction_builder_fn
	from distributed_pair_sentence_classification.interaction_distillation_model_fn import model_fn_builder as interaction_distillation_builder_fn
	from embed_model_fn import model_fn_builder as embed_model_fn_builder
	from model_feature_distillation_fn import model_fn_builder as feature_distillation_fn_builder
	from model_mdd_distillation import model_fn_builder as mdd_distillation_fn_builder
	from model_relation_distillation import model_fn_builder as rkd_distillation_fn_builder
	from distributed_pair_sentence_classification.interaction_rkd_distillation_model_fn import model_fn_builder as interaction_rkd_distillation
	# from pretrain_finetuning.classifier_fn_estimator import classifier_model_fn_builder as bert_pretrain_finetuning
	
	from pretrain_finetuning.classifier_fn_tpu_estimator import classifier_model_fn_builder as bert_pretrain_finetuning

	from model_distillation_adv_adaptation import model_fn_builder as model_distillation_adv_adaptation_build_fn 
	from distributed_gpt.model_fn import model_fn_builder as gpt_lm_builder_fn
	from chid_nlpcc2019.model_fn import model_fn_builder as chid_model_fn_builder
	from chid_nlpcc2019.model_fn_crf import model_fn_builder as chid_crf_model_fn_builder
	from pretrain_finetuning.classifier_fn_tpu_bert_seq_estimator import classifier_model_fn_builder as bert_seq_model_fn_builder 
	from pretrain_finetuning.classifier_fn_tpu_gatedcnn_estimator import classifier_model_fn_builder as gatedcnn_model_fn_builder

import tensorflow as tf

def model_fn_interface(FLAGS):
	print("==apply {} {} model fn builder==".format(FLAGS.task_type, FLAGS.distillation))
	if FLAGS.task_type in ["single_sentence_classification", 
							"single_sentence_multilabel_classification",
							"single_sentence_multilabel_classification_bert",
							"single_sentence_classification_bert"]:
		if FLAGS.distillation == "distillation":
			return model_distillation_builder_fn
		elif FLAGS.distillation == "normal":
			return model_fn_builder
		elif FLAGS.distillation == "feature_distillation":
			return feature_distillation_fn_builder
		elif FLAGS.distillation == "mdd_distillation":
			return mdd_distillation_fn_builder
		elif FLAGS.distillation == "rkd_distillation":
			return rkd_distillation_fn_builder
		elif FLAGS.distillation == "adv_adaptation_distillation":
			return model_distillation_adv_adaptation_build_fn
		else:
			return model_fn_builder
	elif FLAGS.task_type in ["pair_sentence_classification"]:
		if FLAGS.distillation == "normal":
			return bert_nli_builder_fn
		else:
			return bert_nli_builder_fn
	elif FLAGS.task_type in ["interaction_pair_sentence_classification"]:
		if FLAGS.distillation == "normal":
			return interaction_builder_fn
		elif FLAGS.distillation == "distillation":
			return interaction_distillation_builder_fn
		elif FLAGS.distillation == "rkd_distillation":
			return interaction_rkd_distillation
		else:
			return interaction_builder_fn
	elif FLAGS.task_type in ["embed_sentence_classification"]:
		return embed_model_fn_builder
	elif FLAGS.task_type in ['bert_pretrain']:
		return bert_pretrain_finetuning
	elif FLAGS.task_type in ['gpt_pretrain']:
		return gpt_lm_builder_fn
	elif FLAGS.task_type in ['bert_chid']:
		return chid_model_fn_builder
	elif FLAGS.task_type in ['bert_chid_crf']:
		return chid_crf_model_fn_builder
	elif FLAGS.task_type in ['bert_seq_lm']:
		tf.logging.info("****** bert seq lm ******* ")
		return bert_seq_model_fn_builder
	elif FLAGS.task_type in ['gatedcnn_seq_lm']:
		tf.logging.info("****** bert gatedcnn_seq_lm ******* ")
		return gatedcnn_model_fn_builder
