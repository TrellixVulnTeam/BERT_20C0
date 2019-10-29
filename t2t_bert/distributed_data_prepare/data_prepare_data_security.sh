python ./t2t_bert/distributed_data_prepare/classification_data_prepare.py \
	--buckets /data/xuht \
	--train_file data_security/model/textcnn/data/textcnn_train.txt \
	--dev_file data_security/model/textcnn/data/textcnn_dev.txt \
	--test_file data_security/model/textcnn/data/textcnn_dev.txt \
	--train_result_file data_security/model/textcnn/data/train_tfrecords \
	--dev_result_file  data_security/model/textcnn/data/dev_tfrecords\
	--test_result_file  data_security/model/textcnn/data/test_tfrecords\
	--vocab_file ./data/chinese_L-12_H-768_A-12/vocab.txt \
	--label_id /data/xuht/data_security/model/textcnn/data/label_dict.json \
	--lower_case True \
	--max_length 64 \
	--if_rule "no_rule" \
	--rule_word_dict /data/xuht/porn/rule/rule/phrases.json \
	--rule_word_path /data/xuht/porn/rule/rule/mined_porn_domain_adaptation_v2.txt \
	--rule_label_dict /data/xuht/porn/rule/rule/rule_label_dict.json \
	--with_char "no" \
	--char_len 5 \
	--predefined_vocab_size 50000 \
	--corpus_vocab_path sentence_embedding/new_data/data/char_id.txt \
	--data_type fasttext \
	--tokenizer_type "full_bpe" \
	--label_type 'multi_label'
