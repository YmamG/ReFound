# Public AI matching — experimental branch

Branch `feature/public-ai-matching` exposes `/reports/<uuid>/ai-preview/` to visitors without login. Public report details and matches pages link to it. Hidden reports return 404; private contacts/messages are never exposed. No report status or ownership changes automatically. Mainline contains only non-AI refinements.

The branch defaults `REFOUND_AI_PREVIEW_ENABLED=True`; set it to False to disable inference. Missing optional packages/model or inference failures visibly fall back to rules. The endpoint is rate-limited independently of submissions (the configured REFOUND_RATE_LIMIT per IP per ten minutes). A busy inference lock returns rule results immediately rather than queueing another model request.

## Enable explicitly

In a separate optional environment with Sentence Transformers, install the application's ordinary requirements as well. No ML package is added to the normal production requirements. The measured existing evaluation environment uses `sentence-transformers==4.1.0`. Use `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42` (384 dimensions, 128 tokens, no E5 query/passage prefixes). Model assets must be provisioned locally and never committed.

Set `REFOUND_AI_PREVIEW_ENABLED=True` and `REFOUND_AI_MODEL_PATH` to the local SentenceTransformer snapshot directory, then restart Django. Inference is offline (`local_files_only=True`, CPU, remote code disabled). Missing dependency/path/model/inference errors use the rule-based fallback and label it explicitly. Disabled requests never import ML packages. No downloads happen during a request.

Start with one preview worker: the cached model uses memory once per process. One lock serializes startup and inference within the worker. No vector database, API or background queue is introduced. Up to the latest 200 visible, unresolved opposite-type reports in the same building and archive age are compared; truncation is displayed. Only public title/description enter the model. The short preview recomputes embeddings and has no persistent embedding cache yet.

Ranking uses 65% existing rule points and 35% nonnegative text cosine. **These are provisional engineering weights, not tuned or validated parameters.** No previous held-out set was used. There is no acceptance threshold. The independent card search is unchanged by this flag. Real-world bilingual failures remain a reason to treat public AI results as experimental suggestions and collect feedback before relying on them.

## Actual offline smoke — 12 November 2026

Existing Linux CPU environment, 2 Torch threads, 3 eligible synthetic found reports + 1 Arabic query:

| Measurement | Observed |
| --- | ---: |
| Model startup including lazy library import | 7.512 s |
| First 4-text inference and query | 0.425 s |
| Warm 4-text inference and query | 0.043 s |
| Process peak RSS (including Django/imports/model) | 767.9 MiB |
| Snapshot files | 476.4 MiB |

Black laptop bag ranked first for “حقيبة لابتوب سوداء” (cosine 0.7093), then red backpack, then leather wallet. This is a pipeline smoke, **not an accuracy estimate**. Measurements are for this Linux machine and batch, not Windows benchmarks or a hosting capacity guarantee. A 512 MB host is insufficient for this measured process; keep the ordinary rule-based app separate from ML if using such a host.

Reproduce in an optional ML environment:

```bash
python scripts/check_ai_preview.py --model-path /absolute/path/to/offline/snapshot
```

The script uses disposable SQLite and fictional reports, checks candidate exclusions, measures startup/inference/storage/Linux RSS, then deletes its data. It never writes production reports or deploys. Future work: collect staff judgments, inspect language-specific errors, measure realistic batches/concurrency, then decide on caching and public integration. No paid service is required.

## Windows setup on the experimental branch

```powershell
git switch feature/public-ai-matching
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-ai.txt
python scripts/download_ai_model.py --output local-models/minilm
python manage.py migrate
```

Copy the printed absolute model directory into `REFOUND_AI_MODEL_PATH` in `.env`, set `REFOUND_AI_PREVIEW_ENABLED=True`, then restart `python manage.py runserver`. Open a report and choose the experimental AI matching link. Provisioning downloads only the pinned MiniLM snapshot (about 476 MiB), not CLIP or other models. `local-models/` is ignored by Git. Until provisioning is complete the visitor page works with a clearly labeled rules fallback; it must not be presented as actual AI inference.

No hosting deployment occurs when pushing a Git branch. Existing `main` users keep their ordinary application until they explicitly check out or deploy this branch.
