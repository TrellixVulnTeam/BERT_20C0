nohup python ./t2t_bert/distributed_bin/tpu_train_eval_api.py \
	--buckets "gs://yyht_source/pretrain" \
	--config_file "./data/uncased_L-12_H-768_A-12/bert_config_tiny.json" \
	--init_checkpoint "" \
	--vocab_file "./data/uncased_L-12_H-768_A-12/vocab.txt" \
	--label_id "./data/lcqmc/label_dict.json" \
	--max_length 512 \
	--train_file "english_corpus/pretrain_single_random_gan_uncased/chunk_0.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_1.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_2.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_3.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_4.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_5.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_6.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_7.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_8.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_9.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_10.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_11.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_12.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_13.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_14.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_15.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_16.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_17.tfrecords" \
	--dev_file "english_corpus/pretrain_single_random_gan_uncased/chunk_18.tfrecords,english_corpus/pretrain_single_random_gan_uncased/chunk_19.tfrecords" \
	--model_output "model/tiny/english/bert_tiny_with_single_random_adam_decay_40_mixed_mask_uncased" \
	--epoch 40 \
	--num_classes 2 \
	--train_size 11000000 \
	--eval_size 1100000 \
	--batch_size 384 \
	--model_type "bert" \
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
	--init_lr 2e-4 \
	--num_tpu_cores 8 \
	--do_train true \
	--tpu_name "albert1" \
	--mode "pretrain" \




