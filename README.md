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

## Deploy App To Google Cloud Run

This deploys the FastAPI app and static frontend to Cloud Run using Google GenAI for text analysis and Google Cloud Speech-to-Text for audio transcription.

Set deployment variables:

```bash
PROJECT_ID=your-google-cloud-project-id
REGION=us-central1
SERVICE_NAME=gemmaglot-app
AR_REPO_NAME=gemmaglot-app
MODEL=gemma-4-31b-it
```

Authenticate and select the project:

```bash
gcloud auth login
gcloud config set project "$PROJECT_ID"
```

Enable required APIs:

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  speech.googleapis.com
```

Store the Google GenAI API key in Secret Manager:

```bash
read -rsp "Google API key: " GOOGLE_API_KEY
echo

if gcloud secrets describe GOOGLE_API_KEY >/dev/null 2>&1; then
  printf '%s' "$GOOGLE_API_KEY" | gcloud secrets versions add GOOGLE_API_KEY --data-file=-
else
  printf '%s' "$GOOGLE_API_KEY" | gcloud secrets create GOOGLE_API_KEY --data-file=-
fi

unset GOOGLE_API_KEY
```

Create the Artifact Registry repository:

```bash
gcloud artifacts repositories create "$AR_REPO_NAME" \
  --repository-format=docker \
  --location="$REGION"
```

If the repository already exists, continue.

Build and push the app image:

```bash
gcloud builds submit . \
  --config deploy/app/cloudbuild.yaml \
  --substitutions=_LOCATION="$REGION",_REPO_NAME="$AR_REPO_NAME",_SERVICE_NAME="$SERVICE_NAME"
```

Grant the Cloud Run runtime service account access to Speech-to-Text:

```bash
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/speech.client"
```

Deploy the app:

```bash
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO_NAME/$SERVICE_NAME"

gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE" \
  --region="$REGION" \
  --allow-unauthenticated \
  --cpu=1 \
  --memory=1Gi \
  --max-instances=1 \
  --timeout=300 \
  --port=8000 \
  --set-env-vars=PROVIDER=google,MODEL="$MODEL",GOOGLE_CLOUD_PROJECT="$PROJECT_ID",GOOGLE_CLOUD_LOCATION=us,SPEECH_LANGUAGE_CODE=es-US,SPEECH_MODEL=chirp_3,VLLM_TIMEOUT_SECONDS=300 \
  --update-secrets=GOOGLE_API_KEY=GOOGLE_API_KEY:latest
```

Smoke test the deployment:

```bash
SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')"

curl "$SERVICE_URL/api/health"
curl -X POST "$SERVICE_URL/api/auth/demo"
```

The public demo path uses `POST /api/auth/demo` to create an isolated temporary demo user, so reviewers can use history without creating an account.

By default this deployment uses SQLite inside the Cloud Run container. That is fine for a short public demo, but history is not durable across instance restarts. For persistent production history, deploy Cloud SQL MySQL and set `DATABASE_URL` as a Secret Manager secret.

### Rebuild and redeploy after code changes

Use the same shell variables from the first deployment. If you are in a fresh terminal, set them again:

```bash
PROJECT_ID=your-google-cloud-project-id
REGION=us-central1
SERVICE_NAME=gemmaglot-app
AR_REPO_NAME=gemmaglot-app
MODEL=gemma-4-31b-it

gcloud config set project "$PROJECT_ID"
```

After changing backend or frontend code, rebuild and push a new app image:

```bash
gcloud builds submit . \
  --config deploy/app/cloudbuild.yaml \
  --substitutions=_LOCATION="$REGION",_REPO_NAME="$AR_REPO_NAME",_SERVICE_NAME="$SERVICE_NAME"
```

Then redeploy the Cloud Run service with the same runtime settings:

```bash
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO_NAME/$SERVICE_NAME"

gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE" \
  --region="$REGION" \
  --allow-unauthenticated \
  --cpu=1 \
  --memory=1Gi \
  --max-instances=1 \
  --timeout=300 \
  --port=8000 \
  --set-env-vars=PROVIDER=google,MODEL="$MODEL",GOOGLE_CLOUD_PROJECT="$PROJECT_ID",GOOGLE_CLOUD_LOCATION=us,SPEECH_LANGUAGE_CODE=es-US,SPEECH_MODEL=chirp_3,VLLM_TIMEOUT_SECONDS=300 \
  --update-secrets=GOOGLE_API_KEY=GOOGLE_API_KEY:latest
```

If only environment variables or secrets changed, skip the build step and run only `gcloud run deploy`.

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
