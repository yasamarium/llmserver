import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Automatically load environment variables from .env file if it exists
load_dotenv()

class Settings:
    # Server network settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Security
    API_KEY: str = os.getenv("API_KEY", "")

    # Model settings
    MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen3-4b")
    MODEL_FILE: str = os.getenv("MODEL_FILE", "qwen3-4b-instruct-q4_k_m.gguf")
    MODEL_PATH: str = os.getenv(
        "MODEL_PATH",
        str(Path(__file__).resolve().parent.parent / "models" / os.getenv("MODEL_FILE", "qwen3-4b-instruct-q4_k_m.gguf")),
    )
    MODEL_URL: str = os.getenv(
        "MODEL_URL",
        "https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf",
    )
    MODEL_SHA256: Optional[str] = os.getenv("MODEL_SHA256", None)

    # CPU Optimization & Inference settings
    # Default threads to CPU count or fallback to 2 (standard GitHub Actions runner)
    THREADS: int = int(os.getenv("THREADS", str(os.cpu_count() or 2)))
    CONTEXT_SIZE: int = int(os.getenv("CONTEXT_SIZE", "2048"))
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "512"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "512"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))

    # Testing & Development: If True, uses a simulated mock inference engine
    MOCK_MODEL: bool = os.getenv("MOCK_MODEL", "false").lower() in ("true", "1", "yes")

    # Periodic restart interval (seconds) - 5 hours default = 18000 seconds
    RESTART_INTERVAL_SECONDS: int = int(os.getenv("RESTART_INTERVAL_SECONDS", "18000"))


settings = Settings()
