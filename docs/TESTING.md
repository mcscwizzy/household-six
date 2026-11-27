# Testing

Install the runtime dependencies in a Python 3.12 virtual environment before running tests.

```sh
python -m pip install --require-hashes -r requirements.lock
HOUSEHOLD_SIX_LIVE=1 python -m unittest discover -s tests -v
python -m compileall -q app tests scripts
npm ci
npx playwright install --with-deps chromium webkit
```

Run the browser journeys against a fresh data directory and a loopback HTTP instance.

```sh
DATA_DIR="$(mktemp -d)" APP_URL=http://127.0.0.1:3000 python -m app.server
npm run test:e2e
```

Browser tests create synthetic data and capture PNGs in `artifacts/e2e`. They exercise household screens with Chromium and WebKit, including 320, 375, 390, 430, 768, 1024 and 1440 px viewports. Run them on a disposable application instance.

The Compose smoke script checks the existing session and household data across a restart. Use a disposable Compose project name, named volumes, a loopback port and a unique `CI_RUN_ID`. For local AI and MCP tests see [the AI evaluation](AI_EVALUATION.md) and [the private MCP guide](MCP.md).
