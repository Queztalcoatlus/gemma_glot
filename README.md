# GemmaGlot

GemmaGlot is a single-page language-learning app for Spanish text and audio analysis. It serves a React UI from FastAPI and can use Google GenAI or a Gemma model hosted behind vLLM's OpenAI-compatible API.

## Run locally

```bash
uv sync
uv run uvicorn backend.app.main:app --reload
```

Open http://127.0.0.1:8000.

## Run with Docker

Build the app image:

```bash
docker build -t gemmaglot -f deploy/app/Dockerfile .
```

Run it with your local `.env` file:

```bash
docker run --rm --env-file .env -p 8000:8000 gemmaglot
```

Or use Docker Compose:

```bash
docker compose -f deploy/app/compose.yaml up --build
```

The container serves the FastAPI backend and static frontend on port `8000`.
Set `PORT` at runtime if your host requires a different port.

Without a Google API key, the Google provider returns deterministic mock analysis so the UI and request flow are usable during development.

The app now requires a local account. Register from the first screen, then analyze text/audio and review saved history from the Review tab.

## Test

```bash
uv run python -m unittest discover -s backend/tests
```

## Environment

Create `.env` in the repo root:

```env
GOOGLE_API_KEY=...
PROVIDER=google
MODEL=gemma-4-31b-it
GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=us
SPEECH_LANGUAGE_CODE=es-US
SPEECH_MODEL=chirp_3
VLLM_BASE_URL=http://localhost:8001/v1
VLLM_API_KEY=
VLLM_TIMEOUT_SECONDS=300
DATABASE_URL=mysql+pymysql://gemma_glot:your_password_here@localhost:3306/gemma_glot
```

Shell environment variables still work and take priority over `.env`.

`GOOGLE_API_KEY` is Google GenAI API auth and works locally or in deployment. The `GOOGLE_CLOUD_*` and `SPEECH_*` variables configure Google Cloud Speech-to-Text for audio in Google provider mode.

If native Gemma audio hosting is unavailable, Google provider mode automatically transcribes audio with Google Cloud Speech-to-Text before sending the transcript to the configured Google model:

```env
PROVIDER=google
GOOGLE_CLOUD_PROJECT=your-google-cloud-project-id
GOOGLE_CLOUD_LOCATION=us
SPEECH_LANGUAGE_CODE=es-US
SPEECH_MODEL=chirp_3
```

Enable the Speech-to-Text API first:

```bash
gcloud services enable speech.googleapis.com
```

For local development, authenticate Application Default Credentials:

```bash
gcloud auth application-default login
```

In this fallback mode, IPA is inferred from the ASR transcript instead of directly from the original audio signal, so speaker-specific dialect features may be lost.

If `DATABASE_URL` is omitted, the app uses a local SQLite database at `.data/gemma_glot.db`. For MySQL, create a database/user first:

```sql
CREATE DATABASE gemma_glot;
CREATE USER 'gemma_glot'@'localhost' IDENTIFIED BY 'your_password_here';
GRANT ALL PRIVILEGES ON gemma_glot.* TO 'gemma_glot'@'localhost';
FLUSH PRIVILEGES;
```

For vLLM-hosted text and audio analysis:

```env
PROVIDER=vllm
MODEL=google/gemma-4-E2B-it
VLLM_BASE_URL=http://127.0.0.1:8001/v1
VLLM_API_KEY=
VLLM_TIMEOUT_SECONDS=300
```

Run your vLLM server on a different port from the FastAPI app.

For audio uploads, the configured vLLM model must support audio inputs through the OpenAI-compatible chat completions API.

## Run vLLM on WSL

Use a separate Python environment for vLLM. The app only calls vLLM over HTTP, so vLLM does not need to be installed in this repo's `.venv`.

```bash
mkdir -p ~/tools/vllm-env
cd ~/tools/vllm-env
uv venv --python 3.12
source .venv/bin/activate
```

Install vLLM with audio support:

```bash
uv pip install -U "vllm[audio]" --pre \
  --extra-index-url https://wheels.vllm.ai/nightly/cu129 \
  --extra-index-url https://download.pytorch.org/whl/cu129 \
  --index-strategy unsafe-best-match
```

Install the system build tools vLLM/PyTorch may need for runtime kernels:

```bash
sudo apt update
sudo apt install -y build-essential python3.12-dev
```

Start the regular Gemma 4 E2B model:

```bash
VLLM_USE_FLASHINFER_SAMPLER=0 vllm serve google/gemma-4-E2B-it \
  --host 127.0.0.1 \
  --port 8001 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.88 \
  --limit-mm-per-prompt '{"image":0,"audio":1}' \
  --enforce-eager
```

Notes:

- Keep `VLLM_USE_FLASHINFER_SAMPLER=0` on WSL if vLLM errors with missing `nvcc` or `CUDA_HOME`.
- `--limit-mm-per-prompt` must be JSON for recent vLLM versions.
- If vLLM reports low free GPU memory, lower `--gpu-memory-utilization` to `0.86` or `0.84`.
- If you start vLLM with `--api-key`, set the same value in `VLLM_API_KEY`.
