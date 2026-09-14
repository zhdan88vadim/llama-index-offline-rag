import os
from pathlib import Path

# Offline-режим ДО импорта transformers
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def _path(key: str, default: str) -> Path:
    return Path(os.getenv(key, default)).resolve()


def _int(key: str, default: int) -> int:
    return int(os.getenv(key, str(default)))


BASE_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = _path("DATA_PATH", str(BASE_DIR / "data" / "policies"))
PERSIST_DIR = _path("PERSIST_DIR", str(BASE_DIR / "storage"))
MANIFEST_PATH = PERSIST_DIR / "manifest.json"
BM25_PERSIST_DIR = PERSIST_DIR / "bm25"
QDRANT_PATH = PERSIST_DIR / "qdrant"
QDRANT_COLLECTION = "policies"
HISTORY_DB_PATH = PERSIST_DIR / "history.db"

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
RAG_MODEL = os.getenv("RAG_MODEL", "gemma2:9b")
RAG_NUM_CTX = _int("RAG_NUM_CTX", 8192)
RAG_TIMEOUT = _int("RAG_TIMEOUT", 700)

EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-large")
EMBED_DEVICE = os.getenv("EMBED_DEVICE", "cpu")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")

CHUNK_SIZE = _int("CHUNK_SIZE", 512)
CHUNK_OVERLAP = _int("CHUNK_OVERLAP", 64)
MD_FALLBACK_LIMIT = _int("MD_FALLBACK_LIMIT", 1500)

PDF_MIN_CHARS = _int("PDF_MIN_CHARS", 50)
HTML_MIN_CHARS = _int("HTML_MIN_CHARS", 50)

SUPPORTED_EXTS = [".md", ".docx", ".pdf", ".html", ".htm"]
