# syntax=docker/dockerfile:1
ARG VLLM_IMAGE=vllm/vllm-openai:latest
FROM ${VLLM_IMAGE}

ARG MODEL_NAME=google/gemma-4-E4B-it

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends cuda-compat-12-9 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir "vllm[audio]"

ENV HF_HOME=/model-cache \
    MODEL_NAME=${MODEL_NAME} \
    MAX_MODEL_LEN=4096 \
    MAX_NUM_SEQS=1 \
    GPU_MEMORY_UTILIZATION=0.85 \
    ENFORCE_EAGER=1 \
    LD_LIBRARY_PATH=/usr/local/cuda/compat:/usr/local/nvidia/lib64:/usr/local/nvidia/lib:${LD_LIBRARY_PATH}

RUN --mount=type=secret,id=HF_TOKEN \
    HF_TOKEN="$(cat /run/secrets/HF_TOKEN)" hf download "${MODEL_NAME}"

ENV HF_HUB_OFFLINE=1

COPY start-vllm.sh /usr/local/bin/start-vllm.sh
RUN chmod +x /usr/local/bin/start-vllm.sh

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/start-vllm.sh"]
