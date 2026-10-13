import math
from app.rag.chunking.base import ChunkData
from app.rag.parsing.base import Element


def estimate_tokens(text: str) -> int:
    """Fast approximation of token count based on whitespace and punctuation."""
    words = len(text.split())
    # Typically 1 word ~= 1.3 tokens in English
    return max(1, math.ceil(words * 1.3))


def split_text_recursive(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    """Recursively split text by paragraph, sentence, and word to respect max_tokens."""
    if estimate_tokens(text) <= max_tokens:
        return [text.strip()] if text.strip() else []

    separators = ["\n\n", "\n", ". ", " "]
    chunks: list[str] = []

    for sep in separators:
        if sep in text:
            parts = text.split(sep)
            current_chunk: list[str] = []
            current_tokens = 0

            for part in parts:
                part_tokens = estimate_tokens(part)
                if current_tokens + part_tokens > max_tokens and current_chunk:
                    chunk_str = sep.join(current_chunk).strip()
                    if chunk_str:
                        chunks.append(chunk_str)
                    
                    # Retain overlap from end of current chunk
                    current_chunk = current_chunk[-1:] if len(current_chunk) > 1 else []
                    current_tokens = sum(estimate_tokens(p) for p in current_chunk)

                current_chunk.append(part)
                current_tokens += part_tokens

            if current_chunk:
                chunk_str = sep.join(current_chunk).strip()
                if chunk_str:
                    chunks.append(chunk_str)

            return chunks

    # Hard split fallback
    words = text.split()
    step = max(1, max_tokens - overlap_tokens)
    return [" ".join(words[i : i + max_tokens]) for i in range(0, len(words), step)]


class RecursiveChunker:
    """Splits elements using recursive text splitting without structural headers."""

    def __init__(self, max_tokens: int = 400, overlap_tokens: int = 50):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, elements: list[Element], doc_title: str) -> list[ChunkData]:
        chunks: list[ChunkData] = []
        ordinal = 0

        for el in elements:
            splits = split_text_recursive(el.text, self.max_tokens, self.overlap_tokens)
            for split_text in splits:
                chunks.append(
                    ChunkData(
                        content=split_text,
                        token_count=estimate_tokens(split_text),
                        page_start=el.page_number,
                        page_end=el.page_number,
                        section_path=el.heading_path,
                        ordinal=ordinal,
                    )
                )
                ordinal += 1

        return chunks
