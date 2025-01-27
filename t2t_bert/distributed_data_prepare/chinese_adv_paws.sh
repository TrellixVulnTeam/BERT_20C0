python ./t2t_bert/distributed_data_prepare/bert_classification_prepare.py \
	--buckets /data/xuht \
	--train_file baifendian_data/train_only.json \
	--dev_file baifendian_data/dev_only.json \
	--test_file baifendian_data/dev_only.json \
	--train_result_file baifendian_data/train_tfrecords_only \
	--dev_result_file baifendian_data/dev_tfrecords_only \
	--test_result_file baifendian_data/test_tfrecords_only \
	--supervised_distillation_file porn/clean_data/bert_small/train_distillation.info \
	--unsupervised_distillation_file porn/clean_data/bert_small/dev_distillation.info \
	--vocab_file ./data/chinese_L-12_H-768_A-12/vocab.txt \
	--label_id ./data/lcqmc/label_dict.json \
	--lower_case True \
	--max_length 196 \
	--if_rule "no_rule" \
	--rule_word_dict /data/xuht/porn/rule/rule/phrases.json \
	--rule_word_path /data/xuht/porn/rule/rule/mined_porn_domain_adaptation_v2.txt \
	--rule_label_dict /data/xuht/porn/rule/rule/rule_label_dict.json \
	--with_char "no" \
	--char_len 5 \
	--predefined_vocab_size 50000 \
	--corpus_vocab_path porn/clean_data/bert_small/char_id.txt \
	--data_type "mrc_search"