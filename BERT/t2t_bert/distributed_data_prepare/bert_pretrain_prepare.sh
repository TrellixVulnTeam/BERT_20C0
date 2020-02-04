python ./t2t_bert/data_generator/my_create_pretrain_data.py \
	--buckets /data/xuht \
	--input_file /data/xuht/mrc_search/sentence_piece/bert_spm_pretrain_segmented.txt \
	--output_file /data/xuht/mrc_search/sentence_piece/bert_pretrain/mrc_pretrain.tfrecords \
	--vocab_file ./data/chinese_L-12_H-768_A-12/vocab.txt \
	--word_piece_model mrc_search/sentence_piece/mrc_search_bpe.model \
	--do_lower_case true \
	--max_seq_length 384 \
	--max_predictions_per_seq 10 \
	--dupe_factor 2 \
	--tokenizer_type 'word_piece' \
	--do_whole_word_mask true