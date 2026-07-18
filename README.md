# MARS - Multi-Agent Research System for Science

## Running locally

Baseline backend (FastAPI, port 8000):

```bash
uv run fastapi dev src/mars/baseline_app.py
```

If `uv` is not available, create a local virtual environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[server]'
.venv/bin/uvicorn mars.baseline_app:app --host 127.0.0.1 --port 8000
```

Requires `GEMINI_API_KEY` and `SEMANTIC_SCHOLAR_API_KEY` in `.env`.

The original full MARS research pipeline remains available as an optional
local install:

```bash
uv run --extra full fastapi dev src/mars/app.py
```

The full pipeline additionally requires `LANGEXTRACT_API_KEY`.

Session state is temporary: Vercel deployments use the project's Runtime Cache
for six hours, while local development uses an in-memory fallback. No database
or database environment variables are required.

Frontend (Next.js, port 3000):

```bash
cd web-ui
pnpm install
pnpm dev
```

If `pnpm install` reports ignored dependency build scripts, approve them once:

```bash
pnpm approve-builds --all
pnpm install
```

The frontend calls the backend at `http://localhost:8000` (override with `API_URL` in `web-ui/.env.local`). Open http://localhost:3000 for the linear study baseline.

## Recommended formative-study demo path

1. Start the backend and frontend with the commands above.
2. Open `http://localhost:3000`.
3. Enter a research topic and start the discussion.
4. Use the header **Export** button to download the session JSON.
