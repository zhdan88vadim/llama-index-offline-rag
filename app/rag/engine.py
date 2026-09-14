from pathlib import Path

from llama_index.core import PromptTemplate, VectorStoreIndex
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever, QueryFusionRetriever
from llama_index.postprocessor.flag_embedding_reranker import FlagEmbeddingReranker
from llama_index.core.retrievers.fusion_retriever import FUSION_MODES


from .. import config as C
from ..schemas import AnswerStatus, SourceNode
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

    mode: FUSION_MODES = FUSION_MODES.RECIPROCAL_RANK

    hybrid = QueryFusionRetriever(
        [vector_retriever, bm25_retriever],
        similarity_top_k=10,
        num_queries=1,
        mode=mode,
        use_async=False,
        verbose=False,
    )

    qa_prompt = PromptTemplate(
        "Ты — ассистент по внутренним политикам. Используй ТОЛЬКО информацию из контекста.\n"
        "Если в контексте есть прямой ответ — дай его. Если ответа действительно нет — "
        "напиши 'В документах нет информации'.\n\n"
        "Контекст:\n{context_str}\n\nВопрос: {query_str}\nОтвет:"
    )

    reranker = FlagEmbeddingReranker(model=C.RERANKER_MODEL, top_n=5)

    return RetrieverQueryEngine.from_args(
        retriever=hybrid,
        node_postprocessors=[reranker],
        response_mode="compact",
        text_qa_template=qa_prompt,
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
        kind = meta.get("kind") or Path(src).suffix.lower().lstrip(".") or "md"
        if kind == "htm":
            kind = "html"
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
    if "В документах нет информации" in answer:
        return "no_info"
    if not sources:
        return "no_info"
    return "ok"