python ./t2t_bert/distributed_data_prepare/bert_classification_prepare.py \
	--buckets /data/xuht \
	--train_file porn_2/train.txt \
	--dev_file porn_2/test.txt \
	--test_file porn_2/test.txt \
	--train_result_file porn_2/data/train_tfrecords \
	--dev_result_file porn_2/data/dev_tfrecords \
	--test_result_file porn_2/data/test_tfrecords \
	--supervised_distillation_file porn/clean_data/bert_small/train_distillation.info \
	--unsupervised_distillation_file porn/clean_data/bert_small/dev_distillation.info \
	--vocab_file ./data/chinese_L-12_H-768_A-12/vocab.txt \
	--label_id /data/xuht/porn_2/label_dict.json \
	--lower_case "true" \
	--max_length 128 \
	--if_rule "no_rule" \
	--rule_word_dict /data/xuht/porn/rule/rule/phrases.json \
	--rule_word_path /data/xuht/porn/rule/rule/mined_porn_domain_adaptation_v2.txt \
	--rule_label_dict /data/xuht/porn/rule/rule/rule_label_dict.json \
	--with_char "no" \
	--char_len 5 \
	--predefined_vocab_size 50000 \
	--corpus_vocab_path porn/clean_data/bert_small/char_id.txt \
	--data_type "fasttext" \
	--tokenizer_type full_bpe