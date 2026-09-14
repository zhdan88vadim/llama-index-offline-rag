from llama_index.core.ingestion import IngestionPipeline

from .. import config as C
from .parsers import MarkdownThenSentence


def build_pipeline(docstore, vector_store) -> IngestionPipeline:
    return IngestionPipeline(
        transformations=[
            MarkdownThenSentence(
                max_chunk_size=C.CHUNK_SIZE,
                overlap=C.CHUNK_OVERLAP,
                fallback_limit=C.MD_FALLBACK_LIMIT,
            ),
        ],
        docstore=docstore,
        vector_store=vector_store,
    )