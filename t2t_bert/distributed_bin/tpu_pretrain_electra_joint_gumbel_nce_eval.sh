nohup python ./t2t_bert/distributed_bin/tpu_train_eval_api.py \
	--buckets "gs://yyht_source/pretrain" \
	--config_file "./data/roberta_zh_l12_albert/bert_config_tiny.json" \
	--init_checkpoint "" \
	--vocab_file "./data/chinese_L-12_H-768_A-12/vocab.txt" \
	--label_id "./data/lcqmc/label_dict.json" \
	--max_length 512 \
	--train_file "data_single_hard_gan/chunk_0.tfrecords,data_single_hard_gan/chunk_1.tfrecords,data_single_hard_gan/chunk_2.tfrecords,data_single_hard_gan/chunk_3.tfrecords,data_single_hard_gan/chunk_4.tfrecords,data_single_hard_gan/chunk_5.tfrecords,data_single_hard_gan/chunk_6.tfrecords,data_single_hard_gan/chunk_7.tfrecords,data_single_hard_gan/chunk_8.tfrecords,data_single_hard_gan/chunk_9.tfrecords,data_single_hard_gan/chunk_10.tfrecords,data_single_hard_gan/chunk_11.tfrecords,data_single_hard_gan/chunk_12.tfrecords,data_single_hard_gan/chunk_13.tfrecords,data_single_hard_gan/chunk_14.tfrecords,data_single_hard_gan/chunk_15.tfrecords,data_single_hard_gan/chunk_16.tfrecords,data_single_hard_gan/chunk_17.tfrecords" \
	--dev_file "data_single_hard_gan/chunk_18.tfrecords,data_single_hard_gan/chunk_19.tfrecords" \
	-model_output "model/electra_bert_tiny_gen_bert_tiny_dis_joint_gumbel_nce_all_sharing_scale_10" \
	--epoch 15 \
	--num_classes 2 \
	--train_size 11000000 \
	--eval_size 1100000 \
	--batch_size 256 \
	--model_type "albert" \
	--if_shard 1 \
	--is_debug 1 \
	--profiler "no" \
	--train_op "lamb_v2" \
	--load_pretrained "no" \
	--with_char "no_char" \
	--input_target "" \
	--task_type "bert_pretrain" \
	--max_predictions_per_seq 78 \
	--ln_type "postln" \
	--warmup "warmup" \
	--decay "decay" \
	--init_lr 1e-4 \
	--tpu_name "albert3" \
	--num_tpu_cores 8 \
	--mode 'electra' \
	--multi_task_type "generator,discriminator" \
	--multi_task_config "./t2t_bert/pretrain_finetuning/multi_model_gs_gumbel.json" \
	--joint_train "1" \
	--electra_mode "solo_training" \
	--sharing_mode "all_sharing"




