import os
from pathlib import Path

# Load .env if present
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.is_file():
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())


class Config:
    """Application Configuration"""

    SECRET_KEY = os.environ.get("SECRET_KEY") or "tradenza-super-secret-key"
    WTF_CSRF_ENABLED = True

    _base_dir = Path(__file__).resolve().parent
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or f"sqlite:///{_base_dir / 'instance' / 'tradenza.db'}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY", "")
    FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")

    # AI Intelligence & LLM Gateway
    NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
    NVIDIA_BASE_URL = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "nvidia")
    AI_MODEL = os.environ.get("AI_MODEL", "deepseek-ai/deepseek-v4.1-flash")
    OLLAMA_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434")