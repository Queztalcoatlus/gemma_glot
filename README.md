# GemmaGlot

GemmaGlot is a single-page language-learning app for Spanish text and audio analysis. It serves a React UI from FastAPI and can use Google GenAI or a Gemma model hosted behind vLLM's OpenAI-compatible API.

## Run locally

```bash
uv sync
uv run uvicorn backend.app.main:app --reload
```

Open http://127.0.0.1:8000.

Without a Google API key, the Google provider returns deterministic mock analysis so the UI and request flow are usable during development.

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
VLLM_BASE_URL=http://localhost:8001/v1
VLLM_API_KEY=
```

Shell environment variables still work and take priority over `.env`.

For vLLM-hosted text and audio analysis:

```env
PROVIDER=vllm
MODEL=google/gemma-4-E2B-it
VLLM_BASE_URL=http://127.0.0.1:8001/v1
VLLM_API_KEY=
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
