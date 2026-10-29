"""Runtime configuration loaded from environment / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Reduce Chroma noise in CLI/tests unless the user opted in.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

REPO_ROOT = Path(__file__).resolve().parents[2]


def _path(key: str, default: str) -> Path:
    raw = os.getenv(key, default)
    p = Path(raw)
    return p if p.is_absolute() else REPO_ROOT / p


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    azure_api_key: str | None
    azure_endpoint: str | None
    azure_api_version: str
    azure_deployment: str
    azure_embedding_deployment: str
    openai_api_key: str | None
    openai_model: str
    openai_embedding_model: str
    chroma_dir: Path
    docs_dir: Path
    logs_dir: Path
    memory_path: Path
    confidence_threshold: float
    retrieval_top_k: int
    chunk_size: int
    chunk_overlap: int
    collection_name: str = "enterprise_docs"
    max_verify_retries: int = 1


def get_settings() -> Settings:
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "auto").lower(),
        azure_api_key=os.getenv("AZURE_OPENAI_API_KEY") or None,
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT") or None,
        azure_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        azure_embedding_deployment=os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
        ),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        openai_embedding_model=os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        ),
        chroma_dir=_path("CHROMA_DIR", ".chroma"),
        docs_dir=_path("DOCS_DIR", "data/sample_docs"),
        logs_dir=_path("LOGS_DIR", "logs"),
        memory_path=_path("MEMORY_PATH", "logs/memory.json"),
        confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.55")),
        retrieval_top_k=int(os.getenv("RETRIEVAL_TOP_K", "4")),
        chunk_size=int(os.getenv("CHUNK_SIZE", "600")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "80")),
    )
