# Cloud Run vLLM Deployment

This deploys a separate Cloud Run GPU service running vLLM's OpenAI-compatible API for Gemma 4 audio inference.

The web app should call this service with:

```env
PROVIDER=vllm
MODEL=google/gemma-4-E4B-it
VLLM_BASE_URL=https://YOUR_VLLM_SERVICE_URL/v1
VLLM_API_KEY=the-same-secret-value
VLLM_TIMEOUT_SECONDS=600
```

## 1. Set Variables

```bash
PROJECT_ID=your-google-cloud-project
REGION=us-central1
SERVICE_NAME=gemmaglot-vllm
AR_REPO_NAME=gemmaglot-vllm
MODEL_NAME=google/gemma-4-E4B-it
```

`us-central1`, `us-east4`, `europe-west1`, `europe-west4`, and `asia-southeast1` support Cloud Run service GPUs. Start with `us-central1` unless you have a reason to use another region.

## 2. Enable APIs

```bash
gcloud config set project "$PROJECT_ID"

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com
```

## 3. Check GPU Quota

Cloud Run GPU needs `Total Nvidia L4 GPU allocation, per project per region` quota for your chosen region. If deploy fails with a quota error, request quota for 1 L4 GPU in the Google Cloud Quotas page.

## 4. Create Secrets

Create a Hugging Face token with access to the Gemma 4 model, then accept the model terms on Hugging Face before building.

```bash
printf '%s' 'YOUR_HUGGING_FACE_TOKEN' | gcloud secrets create HF_TOKEN --data-file=-
printf '%s' 'CHOOSE_A_RANDOM_VLLM_API_KEY' | gcloud secrets create VLLM_API_KEY --data-file=-
```

Grant the Cloud Build runtime access to the Hugging Face token:

```bash
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

If Cloud Build reports a different service account in a secret access error, grant `roles/secretmanager.secretAccessor` to that service account too.

## 5. Create Artifact Registry

```bash
gcloud artifacts repositories create "$AR_REPO_NAME" \
  --repository-format=docker \
  --location="$REGION"
```

## 6. Build The vLLM Image

```bash
cd deploy/cloud-run-vllm

gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions=_LOCATION="$REGION",_REPO_NAME="$AR_REPO_NAME",_SERVICE_NAME="$SERVICE_NAME",_MODEL_NAME="$MODEL_NAME"
```

This bakes the model weights into the image so Cloud Run cold starts do not have to download the model from Hugging Face.

The Dockerfile installs `cuda-compat-12-9` because the current vLLM image uses a newer CUDA stack than the default Cloud Run NVIDIA L4 driver. The compatibility library path is placed first in `LD_LIBRARY_PATH` so PyTorch can initialize CUDA on Cloud Run.

It also installs `vllm[audio]`; Gemma 4 E2B/E4B audio requests need vLLM's audio extras for PyAV/audio decoding.

## 7. Deploy To Cloud Run

```bash
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO_NAME/$SERVICE_NAME"

gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE" \
  --region="$REGION" \
  --allow-unauthenticated \
  --cpu=8 \
  --memory=32Gi \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --max-instances=1 \
  --concurrency=1 \
  --timeout=600 \
  --port=8000 \
  --no-cpu-throttling \
  --no-gpu-zonal-redundancy \
  --no-deploy-health-check \
  --set-env-vars MODEL_NAME="$MODEL_NAME",MAX_MODEL_LEN=4096,MAX_NUM_SEQS=1,GPU_MEMORY_UTILIZATION=0.85,ENFORCE_EAGER=1 \
  --update-secrets VLLM_API_KEY=VLLM_API_KEY:latest \
  --startup-probe tcpSocket.port=8000,initialDelaySeconds=240,failureThreshold=1,timeoutSeconds=240,periodSeconds=240
```

`--no-deploy-health-check` avoids spending the single approved L4 quota slot during deployment health checks. The first authenticated request will cold-start the model service.

The service is public at the Cloud Run layer, but vLLM requires `Authorization: Bearer VLLM_API_KEY`. Do not expose the API key in frontend JavaScript.

## 8. Test vLLM Directly

```bash
SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')"
VLLM_API_KEY='CHOOSE_A_RANDOM_VLLM_API_KEY'

curl "$SERVICE_URL/v1/models" \
  -H "Authorization: Bearer $VLLM_API_KEY"
```

Then test chat:

```bash
curl "$SERVICE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $VLLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$MODEL_NAME\",
    \"messages\": [{\"role\": \"user\", \"content\": \"Say hello in Spanish.\"}],
    \"max_tokens\": 64
  }"
```

## 9. Connect The Web App

Use the service URL with `/v1` appended:

```env
PROVIDER=vllm
MODEL=google/gemma-4-E4B-it
VLLM_BASE_URL=https://YOUR_SERVICE_URL/v1
VLLM_API_KEY=CHOOSE_A_RANDOM_VLLM_API_KEY
VLLM_TIMEOUT_SECONDS=600
```

## If E4B Does Not Fit

Cloud Run has one NVIDIA L4 GPU with 24 GB VRAM. If E4B fails with out-of-memory or startup errors, rebuild and redeploy with:

```bash
MODEL_NAME=google/gemma-4-E2B-it
```

You can also try `MAX_MODEL_LEN=2048` before falling back to E2B.
