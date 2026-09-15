from pathlib import Path

from llama_index.core import SimpleDirectoryReader
from llama_index.core.schema import Document
from llama_index.readers.file import DocxReader

from .. import config as C
from .extractors import extract_html, extract_pdf

def _make_document(
    rel: str,
    text: str,
    kind: str,
    *,
    page_no: int | None = None,
    file_path: str | None = None,
    extra_meta: dict[str, object] | None = None,
) -> Document:
    """Единая точка создания Document с заполненными метаданными."""
    meta: dict[str, str | int] = {
        "source": rel,
        "source_rel": rel,
        "file_name": rel,
        "kind": kind,
    }
    if file_path is not None:
        meta["file_path"] = file_path
    if page_no is not None:
        meta["page_start"] = page_no
        meta["page_end"] = page_no
    if extra_meta:
        meta.update(extra_meta)

    doc = Document(text=text, metadata=meta)
    doc_id = f"{rel}#p{page_no}" if page_no is not None else rel
    doc.doc_id = doc_id
    doc.id_ = doc_id
    return doc


def load_documents(rel_paths: list[str]) -> list[Document]:
    if not rel_paths:
        return []

    standard = [r for r in rel_paths if Path(r).suffix.lower() in (".md", ".docx")]
    custom = [r for r in rel_paths if Path(r).suffix.lower() in (".pdf", ".html", ".htm")]

    docs: list[Document] = []

    if standard:
        reader = SimpleDirectoryReader(
            input_files=[str(C.DATA_PATH / r) for r in standard],
            file_extractor={".docx": DocxReader()},
            filename_as_id=True,
        )
        for d in reader.load_data():
            fp = Path(d.metadata.get("file_path", "")).resolve()
            try:
                rel = str(fp.relative_to(C.DATA_PATH)).replace("\\", "/")
            except ValueError:
                rel = d.metadata.get("file_name", str(fp))
            kind = fp.suffix.lower().lstrip(".")
            docs.append(
                _make_document(
                    rel,
                    text=d.text,
                    kind=kind,
                    file_path=str(fp),
                    extra_meta={"file_type": kind},
                )
            )

    for rel in custom:
        path = (C.DATA_PATH / rel).resolve()
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            pages = extract_pdf(path)
            kind = "pdf"
        else:
            pages = extract_html(path)
            kind = "html"

        for page_no, text in pages:
            docs.append(
                _make_document(
                    rel,
                    text=text,
                    kind=kind,
                    page_no=page_no,
                    file_path=str(path),
                    extra_meta={"file_type": suffix.lstrip(".")},
                )
            )

    return docs