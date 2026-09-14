from llama_index.core.schema import BaseNode
from llama_index.retrievers.bm25 import BM25Retriever
from Stemmer import Stemmer

from .. import config as C


def build_and_persist_bm25(nodes: list[BaseNode]) -> BM25Retriever:
    C.BM25_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    retriever = BM25Retriever.from_defaults(
        nodes=nodes,
        similarity_top_k=15,
        stemmer=Stemmer("russian"),
        language="russian",
    )
    retriever.persist(str(C.BM25_PERSIST_DIR))
    return retriever


def load_bm25() -> BM25Retriever:
    retriever = BM25Retriever.from_persist_dir(str(C.BM25_PERSIST_DIR))
    retriever.similarity_top_k = 15
    return retriever