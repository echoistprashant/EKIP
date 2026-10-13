from collections import defaultdict
from app.rag.chunking.base import ChunkData
from app.rag.chunking.recursive import estimate_tokens, split_text_recursive
from app.rag.parsing.base import Element


class StructuralChunker:
    """
    Production-grade structural chunker:
    1. Preserves document hierarchy and sections
    2. Groups content under corresponding heading paths
    3. Keeps tables intact or repeats table headers if large
    4. Prepends Contextual Chunk Headers ([Document: ... | Section: ...])
    5. Accurately tracks page spans and ordinal sequences
    """

    def __init__(self, max_tokens: int = 400, overlap_tokens: int = 50):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, elements: list[Element], doc_title: str) -> list[ChunkData]:
        if not elements:
            return []

        # Group non-heading content elements by their heading_path
        section_elements: dict[str, list[Element]] = defaultdict(list)
        section_order: list[str] = []

        for el in elements:
            path = el.heading_path or "General"
            if path not in section_order:
                section_order.append(path)

            # Skip standalone heading elements from being added as paragraph text
            if el.type != "heading":
                section_elements[path].append(el)

        chunks: list[ChunkData] = []
        ordinal = 0

        for path in section_order:
            items = section_elements.get(path, [])
            if not items:
                continue

            combined_text_parts: list[str] = []
            page_numbers: list[int] = []

            for el in items:
                page_numbers.append(el.page_number)
                if el.type == "table":
                    header_preamble = f"[Document: {doc_title} | Section: {path}]\n\n"
                    chunks.append(
                        ChunkData(
                            content=header_preamble + el.text,
                            token_count=estimate_tokens(header_preamble + el.text),
                            page_start=el.page_number,
                            page_end=el.page_number,
                            section_path=path,
                            ordinal=ordinal,
                        )
                    )
                    ordinal += 1
                else:
                    combined_text_parts.append(el.text)

            if not combined_text_parts:
                continue

            full_section_text = "\n\n".join(combined_text_parts)
            p_start = min(page_numbers)
            p_end = max(page_numbers)

            splits = split_text_recursive(full_section_text, self.max_tokens, self.overlap_tokens)

            for part in splits:
                header_preamble = f"[Document: {doc_title} | Section: {path}]\n\n"
                final_content = header_preamble + part

                chunks.append(
                    ChunkData(
                        content=final_content,
                        token_count=estimate_tokens(final_content),
                        page_start=p_start,
                        page_end=p_end,
                        section_path=path,
                        ordinal=ordinal,
                    )
                )
                ordinal += 1

        return chunks
