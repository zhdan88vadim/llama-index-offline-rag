import hashlib
import json
import logging
from pathlib import Path

from .. import config as C

log = logging.getLogger("rag.manifest")


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict[str, str]:
    if C.MANIFEST_PATH.exists():
        try:
            return json.loads(C.MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("Manifest read failed: %s", e)
    return {}


def save_manifest(m: dict[str, str]) -> None:
    C.PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    tmp = C.MANIFEST_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(C.MANIFEST_PATH)


def scan_files() -> dict[str, str]:
    out = {}
    for p in C.DATA_PATH.rglob("*"):
        if p.is_file() and p.suffix.lower() in C.SUPPORTED_EXTS:
            rel = str(p.relative_to(C.DATA_PATH)).replace("\\", "/")
            try:
                out[rel] = file_hash(p)
            except OSError as e:
                log.warning("Не удалось прочитать %s: %s", p, e)
    return out