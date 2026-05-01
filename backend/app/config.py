import os
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
ENV_PATHS = (ROOT / ".env", ROOT / "backend" / ".env")
DEFAULT_MODEL = "gemma-4-26b-a4b-it"
DEFAULT_PROVIDER = "google"
DEFAULT_VLLM_BASE_URL = "http://localhost:8001/v1"


def load_env(paths: Iterable[Path] = ENV_PATHS) -> None:
    """Load simple KEY=VALUE pairs from .env files without overriding the shell."""
    for path in paths:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(raw_line)
            if parsed is None:
                continue
            key, value = parsed
            os.environ.setdefault(key, value)


def get_api_key() -> str | None:
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


def get_provider() -> str:
    provider = os.getenv("PROVIDER", DEFAULT_PROVIDER).strip().lower()
    if provider not in {"google", "vllm"}:
        raise ValueError("PROVIDER must be google or vllm.")
    return provider


def get_model_name() -> str:
    model = os.getenv("MODEL", DEFAULT_MODEL).strip()
    if not model or "=" in model or any(char.isspace() for char in model):
        raise ValueError("MODEL must be a model id like gemma-4-26b-a4b-it.")
    return model


def get_vllm_base_url() -> str:
    return os.getenv("VLLM_BASE_URL", DEFAULT_VLLM_BASE_URL).strip().rstrip("/")


def get_vllm_api_key() -> str | None:
    return os.getenv("VLLM_API_KEY") or None


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[7:].strip()
    if "=" not in stripped:
        return None

    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
        return None

    return key, _clean_value(value.strip())


def _clean_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        quote = value[0]
        value = value[1:-1]
        if quote == '"':
            return value.encode("utf-8").decode("unicode_escape")
        return value

    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    return value
