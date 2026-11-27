# Six local assistant

Six is optional. In the browser, open **More → Six**, choose an action and enter a request. Grocery, calendar, chore and recipe actions create a proposal that an adult must explicitly apply. Household questions read current calendar, chores, shopping, meals or point balances. Document extraction displays text and a summary for review. Requests and results belong to the submitting account and expire after one day.

## Bundled Ollama

```sh
AI_ENABLED=true docker compose --profile six up -d --build
docker compose --profile six exec ollama ollama pull qwen3.5:0.8b
```

The Ollama container has two CPU equivalents, a 4 GB memory limit, one loaded model, one concurrent inference, a 4096-token context and cloud features disabled. The app requests `think: false` and defaults to a two-minute keep-alive. Set `AI_KEEP_ALIVE=0` to unload after each request. The Ollama service has no published port.

For an existing private LAN runtime, set `AI_ENABLED=true` and `AI_BASE_URL=http://<private-LAN-address>:11434` on the application. Install the model and configure local-only mode, queueing and resource limits on the LAN service itself. The app connects only to private addresses and uses one inference worker.

## Extraction

Paste text or attach a UTF-8 text file, PDF, PNG or JPEG up to 550 KB. Build with `WITH_LOCAL_OCR=1` to include Tesseract and the PDF text extractor. Host installs can provide those binaries on `PATH`. Image extraction can use the local vision model when Tesseract is unavailable. PDFs use up to five pages of embedded text. Scan-only PDFs require separate OCR before import.

The queue persists across restarts, accepts eight active jobs and retains up to 50 recent jobs per household. A restarted worker can retry a previously running job once. Model output is limited to typed fields, and the application validates dates, authorization and writes at confirmation.
