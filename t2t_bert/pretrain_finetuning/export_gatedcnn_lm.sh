CUDA_VISIBLE_DEVICES="" python ./t2t_bert/pretrain_finetuning/export_api.py \
 --buckets "/data/xuht" \
 --config_file "/data/xuht/ae_lightcnn/textcnn_multilingual_embedding_light_dgcnn.json" \
 --model_dir "ae_lightcnn/export" \
 --init_checkpoint "ae_lightcnn/model.ckpt-2800000" \
 --model_output "ae_lightcnn/model.ckpt-2800000" \
 --max_length 64 \
 --export_dir "ae_lightcnn/export" \
 --num_classes 2 \
 --input_target "" \
 --model_scope "textcnn" \
 --model_type "gated_cnn_seq" \
 --export_type "gated_cnn_seq" \
 --sharing_mode "all_sharing" \
 --export_model_type "gated_cnn_seq" \
 --mask_type "left2right"