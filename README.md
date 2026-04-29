# GemmaGlot

GemmaGlot is a single-page language-learning app for Spanish text and audio analysis. It serves a React UI from FastAPI and can use Google GenAI or a local Ollama model for text analysis.

## Run locally

```powershell
uv sync
uv run uvicorn backend.app.main:app --reload
```

Open http://127.0.0.1:8000.

Without a Google API key, the app returns deterministic mock analysis so the UI and request flow are usable during development.

## Test

```powershell
uv run python -m unittest discover -s backend/tests
```

## Environment

Create `.env` in the repo root:

```env
GOOGLE_API_KEY=...
PROVIDER=google
MODEL=gemma-4-31b-it
OLLAMA_BASE_URL=http://localhost:11434
```

Shell environment variables still work and take priority over `.env`.

For local Ollama text analysis:

```env
PROVIDER=ollama
MODEL=<your-ollama-model-tag>
OLLAMA_BASE_URL=http://localhost:11434
```

Audio uploads still require a provider/model that accepts raw audio. The Ollama path currently handles text input only.
