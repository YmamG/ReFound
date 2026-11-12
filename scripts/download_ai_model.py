"""Explicit provisioning command; never runs automatically during a web request."""
import argparse
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--output',default='local-models/minilm')
args=parser.parse_args()
from huggingface_hub import snapshot_download
path=snapshot_download(
    repo_id='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
    revision='e8f8c211226b894fcb81acc59f3b34ba3efd5f42',
    local_dir=str(Path(args.output).resolve()),
    allow_patterns=['config.json','modules.json','README.md','sentence_bert_config.json',
        'special_tokens_map.json','model.safetensors','sentencepiece.bpe.model',
        'config_sentence_transformers.json','tokenizer_config.json','unigram.json',
        'tokenizer.json','1_Pooling/config.json'])
print('Set REFOUND_AI_MODEL_PATH to:',path)
