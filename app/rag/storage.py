import qdrant_client
from llama_index.core import StorageContext
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore
from llama_index.vector_stores.qdrant import QdrantVectorStore

from .. import config as C


def get_qdrant_client() -> qdrant_client.QdrantClient:
    C.QDRANT_PATH.mkdir(parents=True, exist_ok=True)
    return qdrant_client.QdrantClient(path=str(C.QDRANT_PATH))


def get_vector_store() -> QdrantVectorStore:
    return QdrantVectorStore(
        client=get_qdrant_client(), collection_name=C.QDRANT_COLLECTION
    )


def get_storage_context() -> StorageContext:
    C.PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    return StorageContext.from_defaults(
        vector_store=get_vector_store(),
        docstore=SimpleDocumentStore(),
        index_store=SimpleIndexStore(),
    )