CUDA_VISIBLE_DEVICES="" python ./t2t_bert/pretrain_finetuning/export_api.py \
 --buckets "/data/xuht" \
 --config_file "/data/xuht/gatedcnn/textcnn_multilingual_embedding_dgcnn.json" \
 --model_dir "gatedcnn/export" \
 --init_checkpoint "gatedcnn/model.ckpt-160000" \
 --model_output "gatedcnn/model.ckpt-160000" \
 --max_length 256 \
 --export_dir "gatedcnn/export" \
 --num_classes 2 \
 --input_target "" \
 --model_scope "textcnn" \
 --model_type "gated_cnn_seq" \
 --export_type "gated_cnn_seq" \
 --sharing_mode "all_sharing" \
 --export_model_type "gated_cnn_seq" \
 --mask_type "left2right"