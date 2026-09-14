import logging
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

from .. import config as C

log = logging.getLogger("rag.extractors")


def extract_pdf(path: Path) -> list[tuple[int | None, str]]:
    """Только текстовый слой. Сканы пропускаются."""
    try:
        reader = PdfReader(str(path))
    except Exception as e:
        log.warning("PDF read failed %s: %s", path, e)
        return []
    pages: list[tuple[int | None, str]] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append((i, text))
    joined = "".join(t for _, t in pages)
    if len(joined) < C.PDF_MIN_CHARS:
        log.info("PDF %s: текстовый слой отсутствует, пропускаем", path.name)
        return []
    return pages


def extract_html(path: Path) -> list[tuple[int | None, str]]:
    try:
        raw = path.read_bytes().decode("utf-8", errors="replace")
    except Exception as e:
        log.warning("HTML read failed %s: %s", path, e)
        return []

    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    clean_text = soup.get_text(separator="\n", strip=True).strip()

    if len(clean_text) < C.HTML_MIN_CHARS:
        log.info("HTML %s: пустой текст, пропускаем", path.name)
        return []
    return [(None, clean_text)]