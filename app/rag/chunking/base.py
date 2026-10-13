from dataclasses import dataclass
from typing import Protocol
from app.rag.parsing.base import Element


@dataclass
class ChunkData:
    """Atomic retrievable chunk representation prior to vector embedding."""
    content: str
    token_count: int
    page_start: int
    page_end: int
    section_path: str
    ordinal: int


class BaseChunker(Protocol):
    """Protocol for chunking strategies."""
    def chunk(self, elements: list[Element], doc_title: str) -> list[ChunkData]:
        ...
