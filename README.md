# MARS - Multi-Agent Research System for Science

## Running locally

Backend (FastAPI, port 8000):

```bash
uv run fastapi dev src/mars/app.py
```

Requires `GEMINI_API_KEY`, `LANGEXTRACT_API_KEY`, and `SEMANTIC_SCHOLAR_API_KEY` in `.env`.

Frontend (Next.js, port 3000):

```bash
cd web-ui
pnpm install
pnpm dev
```

The frontend calls the backend at `http://localhost:8000` (override with `API_URL` in `web-ui/.env.local`). Open http://localhost:3000/canvas.
