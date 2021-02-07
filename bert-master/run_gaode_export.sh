python run_gaode_export.py \
    --vocab_file=/data/albert/roberta_tiny_span_mask_50g_whole/vocab.txt \
    --bert_config_file=/data/albert/roberta_tiny_span_mask_50g_whole/bert_config_tiny.json \
    --init_checkpoint=/data/albert/gaodemrc/roberta_tiny_cls_no_cricle_loss/model.ckpt-78126 \
    --do_train=False \
    --train_file=/data/xuht/finetuning_data/gaodemrc/train_v1.json \
    --do_predict=False \
    --predict_file=/data/xuht/finetuning_data/gaodemrc/dev_v1.json \
    --train_batch_size=32 \
    --num_train_epochs=3 \
    --max_seq_length=384 \
    --doc_stride=128 \
    --learning_rate=3e-5 \
    --save_checkpoints_steps=1000 \
    --output_dir=/data/xuht/roberta_tiny_cls_no_cricle_loss \
    --do_lower_case=True \
    --use_tpu=False \
    --if_multisigmoid=False \
    --num_labels=44