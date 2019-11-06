nohup python ./t2t_bert/distributed_bin/tpu_train_eval_api.py \
	--buckets "gs://yyht_source/pretrain" \
	--config_file "./data/roberta_zh_l12_albert/bert_config_tiny.json" \
	--init_checkpoint "" \
	--vocab_file "./data/chinese_L-12_H-768_A-12/vocab.txt" \
	--label_id "./data/lcqmc/label_dict.json" \
	--max_length 512 \
	--train_file "data_single/chunk_0.tfrecords,data_single/chunk_1.tfrecords,data_single/chunk_2.tfrecords,data_single/chunk_3.tfrecords,data_single/chunk_4.tfrecords,data_single/chunk_5.tfrecords,data_single/chunk_6.tfrecords,data_single/chunk_7.tfrecords,data_single/chunk_8.tfrecords,data_single/chunk_9.tfrecords,data_single/chunk_10.tfrecords,data_single/chunk_11.tfrecords,data_single/chunk_12.tfrecords,data_single/chunk_13.tfrecords,data_single/chunk_14.tfrecords,data_single/chunk_15.tfrecords,data_single/chunk_16.tfrecords,data_single/chunk_17.tfrecords" \
	--dev_file "data_single/chunk_18.tfrecords,data_single/chunk_19.tfrecords" \
	--model_output "model/albert_tiny_factorized_with_single_adam_decay_5" \
	--epoch 5 \
	--num_classes 2 \
	--train_size 11000000 \
	--eval_size 1100000 \
	--batch_size 1024 \
	--model_type "albert" \
	--if_shard 1 \
	--is_debug 1 \
	--profiler "no" \
	--train_op "adam_decay" \
	--load_pretrained "no" \
	--with_char "no_char" \
	--input_target "" \
	--task_type "bert_pretrain" \
	--max_predictions_per_seq 78 \
	--ln_type "postln" \
	--warmup "warmup" \
	--decay "decay" \
	--init_lr 5e-4 \
	--do_train true \
	--tpu_name "htxu91"



