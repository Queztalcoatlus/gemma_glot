#!/usr/bin/env bash
set -euo pipefail

: "${VLLM_API_KEY:?Set VLLM_API_KEY.}"

args=(
  --host 0.0.0.0
  --port "${PORT:-8000}"
  --model "${MODEL_NAME:-google/gemma-4-E4B-it}"
  --api-key "${VLLM_API_KEY}"
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION:-0.85}"
  --max-model-len "${MAX_MODEL_LEN:-4096}"
  --max-num-seqs "${MAX_NUM_SEQS:-1}"
  --limit-mm-per-prompt '{"audio":1}'
)

if [[ "${ENFORCE_EAGER:-1}" == "1" ]]; then
  args+=(--enforce-eager)
fi

exec python3 -m vllm.entrypoints.openai.api_server "${args[@]}"
