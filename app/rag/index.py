import logging

from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
)
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore

from .. import config as C
from .bm25 import build_and_persist_bm25
from .loaders import load_documents
from .manifest import load_manifest, save_manifest, scan_files
from .pipeline import build_pipeline
from .storage import get_storage_context, get_vector_store

log = logging.getLogger("rag.index")


def delete_document(index: VectorStoreIndex, doc_id: str) -> None:
    docstore = index.docstore
    node_ids: list[str] = []
    try:
        ref_info = docstore.get_ref_doc_info(doc_id)
        if ref_info is not None:
            node_ids = list(ref_info.node_ids)
    except Exception:
        pass

    if node_ids:
        try:
            index.delete_nodes(node_ids, delete_from_docstore=True)
        except Exception as e:
            log.warning("delete_nodes(%s) failed: %s", doc_id, e)

    try:
        docstore.delete_document(doc_id, raise_error=False)
    except Exception:
        pass


def sync_index(index: VectorStoreIndex) -> dict:
    pipeline = build_pipeline(index.docstore, index.storage_context.vector_store)
    manifest = load_manifest()
    current = scan_files()

    current_ids = set(current.keys())
    indexed_ids = set(manifest.keys())

    added = sorted(current_ids - indexed_ids)
    removed = sorted(indexed_ids - current_ids)
    changed = sorted(
        i for i in (current_ids & indexed_ids) if current[i] != manifest[i]
    )

    log.info(
        "Sync: added=%d changed=%d removed=%d",
        len(added), len(changed), len(removed),
    )

    for doc_id in removed + changed:
        delete_document(index, doc_id)

    to_load = added + changed
    if to_load:
        docs = load_documents(to_load)
        if docs:
            nodes = pipeline.run(documents=docs, show_progress=True)
            log.info("Ingested %d node(s) из %d doc(s)", len(nodes), len(docs))

    save_manifest(current)
    index.storage_context.persist(str(C.PERSIST_DIR))

    if added or changed or removed:
        all_nodes = list(index.docstore.docs.values())
        if all_nodes:
            build_and_persist_bm25(all_nodes)

    return {
        "added": len(added),
        "changed": len(changed),
        "removed": len(removed),
    }


def build_or_load_index() -> VectorStoreIndex:
    C.PERSIST_DIR.mkdir(parents=True, exist_ok=True)

    persist_ready = (
        (C.PERSIST_DIR / "docstore.json").exists()
        and (C.PERSIST_DIR / "index_store.json").exists()
    )

    if persist_ready:
        log.info("Загружаем индекс из %s", C.PERSIST_DIR)
        storage = StorageContext.from_defaults(
            vector_store=get_vector_store(),
            docstore=SimpleDocumentStore.from_persist_dir(str(C.PERSIST_DIR)),
            index_store=SimpleIndexStore.from_persist_dir(str(C.PERSIST_DIR)),
        )
        index = load_index_from_storage(storage)
        sync_index(index)
        return index

    log.info("Первичная сборка индекса из %s", C.DATA_PATH)
    current = scan_files()
    if not current:
        raise RuntimeError(
            f"Не найдено документов в {C.DATA_PATH} (extensions: {C.SUPPORTED_EXTS})"
        )

    docs = load_documents(sorted(current.keys()))
    storage = get_storage_context()
    pipeline = build_pipeline(storage.docstore, storage.vector_store)
    nodes = pipeline.run(documents=docs, show_progress=True)
    log.info("Создано %d узлов", len(nodes))

    index = VectorStoreIndex(nodes=nodes, storage_context=storage)
    save_manifest(current)
    index.storage_context.persist(str(C.PERSIST_DIR))
    build_and_persist_bm25(nodes)
    return index