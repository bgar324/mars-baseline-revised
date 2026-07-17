# MARS - Multi-Agent Research System for Science

## Running locally

Backend (FastAPI, port 8000):

```bash
uv run fastapi dev src/mars/app.py
```

If `uv` is not available, create a local virtual environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/uvicorn mars.app:app --host 127.0.0.1 --port 8000
```

Requires `GEMINI_API_KEY`, `LANGEXTRACT_API_KEY`, and
`SEMANTIC_SCHOLAR_API_KEY` in `.env`.

For formative-study persistence, also set:

```bash
SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_SECRET_KEY=
```

Apply the schemas in `supabase/migrations/` to the configured Supabase project
before study sessions.

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

The frontend calls the backend at `http://localhost:8000` (override with `API_URL` in `web-ui/.env.local`). Open http://localhost:3000/canvas for MARS or http://localhost:3000/baseline for the linear study baseline.

## Recommended formative-study demo path

1. Start the backend and frontend with the commands above.
2. Open `http://localhost:3000/canvas`.
3. Use manual mode with a short, broad research problem.
4. Let extraction, retrieval, clustering, and persona generation complete.
5. Inspect/edit personas, then select 2-3 researchers for debate.
6. Open the debate node to show conversation and synthesis.
7. Use the header **Export** button to download the session JSON.
