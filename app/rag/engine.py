from pathlib import Path

from llama_index.core import VectorStoreIndex
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever, QueryFusionRetriever
from llama_index.postprocessor.flag_embedding_reranker import FlagEmbeddingReranker
from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
from llama_index.core.response_synthesizers import ResponseMode

from app.rag.prompts import NO_INFO_PHRASE, QA_PROMPT

from .. import config as C
from ..schemas import AnswerStatus, SourceKind, SourceNode
from .bm25 import build_and_persist_bm25, load_bm25


def build_query_engine(index: VectorStoreIndex) -> RetrieverQueryEngine:
    if C.BM25_PERSIST_DIR.exists():
        bm25_retriever = load_bm25()
    else:
        nodes = list(index.docstore.docs.values())
        if not nodes:
            raise RuntimeError("В индексе нет узлов — нечего искать.")
        bm25_retriever = build_and_persist_bm25(nodes)

    vector_retriever = VectorIndexRetriever(index=index, similarity_top_k=15)
    
    hybrid = QueryFusionRetriever(
        [vector_retriever, bm25_retriever],
        similarity_top_k=10,
        num_queries=1,
        mode=FUSION_MODES.RECIPROCAL_RANK,
        use_async=False,
        verbose=False,
    )

    reranker = FlagEmbeddingReranker(model=C.RERANKER_MODEL, top_n=5)

    return RetrieverQueryEngine.from_args(
        retriever=hybrid,
        node_postprocessors=[reranker],
        response_mode=ResponseMode.COMPACT,
        text_qa_template=QA_PROMPT,
    )


def serialize_sources(response) -> list[SourceNode]:
    out: list[SourceNode] = []
    for n in response.source_nodes:
        meta = n.metadata or {}
        src = (
            meta.get("source_rel")
            or meta.get("file_name")
            or Path(meta.get("file_path", "")).name
            or "unknown"
        )

        raw_kind = meta.get("kind") or Path(src).suffix.lower().lstrip(".")
        kind = SourceKind.from_string(raw_kind) if raw_kind else SourceKind.UNKNOWN

        score = n.score if isinstance(n.score, (int, float)) else None
        out.append(SourceNode(
            id=str(getattr(n, "node_id", "") or ""),
            source=str(src),
            kind=kind,
            score=float(score) if score is not None else None,
            snippet=n.text[:300],
            page_start=meta.get("page_start"),
            page_end=meta.get("page_end"),
            title=meta.get("title"),
        ))
    return out


def detect_status(answer: str, sources: list[SourceNode]) -> AnswerStatus:
    if NO_INFO_PHRASE in answer:
        return "no_info"
    if not sources:
        return "no_info"
    return "ok"