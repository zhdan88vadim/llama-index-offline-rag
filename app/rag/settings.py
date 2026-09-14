from llama_index.core import Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama

from .. import config as C


def setup_settings() -> None:
    Settings.llm = Ollama(
        model=C.RAG_MODEL,
        base_url=C.OLLAMA_HOST,
        temperature=0.0,
        context_window=C.RAG_NUM_CTX,
        request_timeout=C.RAG_TIMEOUT,
    )
    Settings.embed_model = HuggingFaceEmbedding(
        model_name=C.EMBED_MODEL,
        device=C.EMBED_DEVICE,
        query_instruction="query: ",
        text_instruction="passage: ",
    )
    Settings.node_parser = SentenceSplitter(
        chunk_size=C.CHUNK_SIZE, chunk_overlap=C.CHUNK_OVERLAP
    )