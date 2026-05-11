# syntax=docker/dockerfile:1
ARG VLLM_IMAGE=vllm/vllm-openai:latest
FROM ${VLLM_IMAGE}

ARG MODEL_NAME=google/gemma-4-E4B-it

ENV HF_HOME=/model-cache \
    MODEL_NAME=${MODEL_NAME} \
    MAX_MODEL_LEN=4096 \
    MAX_NUM_SEQS=1 \
    GPU_MEMORY_UTILIZATION=0.85 \
    ENFORCE_EAGER=1

RUN --mount=type=secret,id=HF_TOKEN \
    HF_TOKEN="$(cat /run/secrets/HF_TOKEN)" hf download "${MODEL_NAME}"

ENV HF_HUB_OFFLINE=1

COPY start-vllm.sh /usr/local/bin/start-vllm.sh
RUN chmod +x /usr/local/bin/start-vllm.sh

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/start-vllm.sh"]
