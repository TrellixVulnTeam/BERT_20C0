python ./t2t_bert/data_generator/create_span_bert_pretrain_dataset_efficiency.py \
	--buckets /data/xuht \
	--input_file /notebooks/source/albert_zh-master/data/news_zh_1.txt \
	--output_file /data/xuht/mrc_search/pretrain/pretrain_debug \
	--vocab_file ./data/chinese_L-12_H-768_A-12/vocab.txt \
	--word_piece_model mrc_search/sentence_piece/mrc_search_bpe.model \
	--do_lower_case true \
	--max_seq_length 384 \
	--max_predictions_per_seq 5 \
	--dupe_factor 10 \
	--tokenizer_type 'word_piece' \
	--do_whole_word_mask true \
	--es_user_name mrc_search_4l \
	--password K9cb1bd713507 \
	--doc_index green_pretrain_debug \
	--doc_type _doc
