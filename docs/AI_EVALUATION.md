# AI evaluation

The most recent recorded live evaluation `test_six_real_model_and_explicit_confirmation` ran against Ollama 0.40.19 and `qwen3.5:0.8b` with a 4096-token context, two CPU equivalents, four GB RAM and one concurrent inference. Six synthetic text prompts passed through the FastAPI job API. They covered grocery, calendar, chores, a household question, recipe extraction and document-text extraction. The grocery test also verified no write before confirmation and a single write after an identical approval replay. This Operation Homefront continuation did not run local model inference, so these results are historical baseline evidence, not a new evaluation.

The attachment test also recovered text from a synthetic PNG by local vision inference and from a text-bearing PDF by local text extraction followed by model inference.

This is a small functional sample, far below the requested 100 fixtures. Broad extraction accuracy, ambiguous prompts, missing information, unknown members, incorrect dates, malformed model output, prompt injection, printed school schedules, multiple events/items, production latency and hardware-specific resource use remain unevaluated. Do not infer accuracy or measured resource utilization from the configured caps.

```sh
AI_ENABLED=true AI_BASE_URL=http://127.0.0.1:11434 \
  HOUSEHOLD_SIX_LIVE=1 HOUSEHOLD_SIX_AI_LIVE=1 \
  python -m unittest discover -s tests -p test_runtime.py -k six_real -v
```
