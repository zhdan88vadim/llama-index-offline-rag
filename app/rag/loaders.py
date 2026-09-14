from pathlib import Path

from llama_index.core import SimpleDirectoryReader
from llama_index.core.schema import Document
from llama_index.readers.file import DocxReader

from .. import config as C
from .extractors import extract_html, extract_pdf


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
            d.metadata["source"] = rel
            d.metadata["source_rel"] = rel
            d.metadata["file_name"] = rel
            d.metadata["kind"] = fp.suffix.lower().lstrip(".")
            d.doc_id = rel
            d.id_ = rel
            docs.append(d)

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
            meta = {
                "source": rel,
                "source_rel": rel,
                "file_name": rel,
                "file_path": str(path),
                "file_type": suffix.lstrip("."),
                "kind": kind,
            }
            if page_no is not None:
                meta["page_start"] = page_no
                meta["page_end"] = page_no
            doc = Document(text=text, metadata=meta)
            doc_id = f"{rel}#p{page_no}" if page_no else rel
            doc.doc_id = doc_id
            doc.id_ = doc_id
            docs.append(doc)

    return docs