from typing import Sequence

from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.core.node_parser.interface import NodeParser
from llama_index.core.schema import BaseNode

from .. import config as C


class MarkdownThenSentence(NodeParser):
    max_chunk_size: int = C.CHUNK_SIZE
    overlap: int = C.CHUNK_OVERLAP
    fallback_limit: int = C.MD_FALLBACK_LIMIT

    inherit_keys: list[str] = [
        "file_name", "file_path", "source", "source_rel",
        "file_type", "file_size", "creation_date", "last_modified_date",
        "page_start", "page_end", "title",
    ]

    def _parse_nodes(
        self, nodes: Sequence[BaseNode], show_progress: bool = False, **kwargs
    ) -> list[BaseNode]:
        md_parser = MarkdownNodeParser()
        sentence_parser = SentenceSplitter(
            chunk_size=self.max_chunk_size, chunk_overlap=self.overlap
        )
        parent_meta = {n.node_id: dict(n.metadata or {}) for n in nodes}
        md_nodes = md_parser._parse_nodes(nodes, show_progress=show_progress, **kwargs)
        self._restore_metadata(md_nodes, parent_meta)

        small: list[BaseNode] = []
        big: list[BaseNode] = []
        for n in md_nodes:
            (big if len(n.text) > self.fallback_limit else small).append(n)

        if big:
            sub_nodes = sentence_parser._parse_nodes(
                big, show_progress=show_progress, **kwargs
            )
            self._restore_metadata(sub_nodes, {n.node_id: n.metadata for n in big})
            small.extend(sub_nodes)
        return small

    def _restore_metadata(self, nodes: list[BaseNode], parent_meta: dict) -> None:
        for n in nodes:
            ref = getattr(n, "ref_doc_id", None)
            meta = parent_meta.get(ref) if ref and ref in parent_meta else {}
            if not meta:
                for m in parent_meta.values():
                    meta.update(m)
            for k in self.inherit_keys:
                if k in meta and k not in n.metadata:
                    n.metadata[k] = meta[k]