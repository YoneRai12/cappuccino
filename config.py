# config.py （完成版）
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    """Application configuration loaded from environment variables."""

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    # ★★★ この行が重要です！ ★★★
    openai_api_base: Optional[str] = os.getenv("OPENAI_API_BASE")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    azure_openai_key: str | None = os.getenv("AZURE_OPENAI_API_KEY")
    fractal_depth: int = int(os.getenv("FRACTAL_DEPTH", "2"))
    fractal_breadth: int = int(os.getenv("FRACTAL_BREADTH", "3"))

settings = Settings()