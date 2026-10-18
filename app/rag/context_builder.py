import math
from dataclasses import dataclass
from typing import Sequence
import uuid

from app.rag.retrieval.base import Candidate


@dataclass
class SourceItem:
    """Represents a numbered source item injected into the prompt."""
    source_id: int
    candidate: Candidate


@dataclass
class BuiltContext:
    """Output of the context assembly pipeline."""
    context_text: str
    sources: list[SourceItem]
    source_map: dict[int, Candidate]
    estimated_tokens: int


class ContextBuilder:
    """
    Assembles retrieved candidates into a token-budgeted, deduplicated,
    and Lost-in-the-Middle mitigated XML context block for the LLM.
    """

    def __init__(self, chars_per_token: float = 3.8) -> None:
        self.chars_per_token = chars_per_token

    def estimate_tokens(self, text: str) -> int:
        return max(1, math.ceil(len(text) / self.chars_per_token))

    def reorder_lost_in_the_middle(self, candidates: list[Candidate]) -> list[Candidate]:
        """
        Reorders ranked candidates according to the Lost-in-the-Middle mitigation strategy
        (Liu et al., 2023). Top-ranked candidates are placed at the beginning and end
        of the context window where LLM attention is strongest.
        """
        if len(candidates) <= 2:
            return list(candidates)

        reordered: list[Candidate | None] = [None] * len(candidates)
        left = 0
        right = len(candidates) - 1

        for idx, candidate in enumerate(candidates):
            if idx % 2 == 0:
                reordered[left] = candidate
                left += 1
            else:
                reordered[right] = candidate
                right -= 1

        return [c for c in reordered if c is not None]

    def build(
        self,
        candidates: Sequence[Candidate],
        max_context_tokens: int = 3000,
        enable_lost_in_middle: bool = True,
    ) -> BuiltContext:
        """
        Filters duplicates, enforces token budget, reorders if enabled,
        and generates structured XML context with 1-based source IDs.
        """
        # Step 1: Deduplicate candidates by chunk_id while preserving order
        unique_candidates: list[Candidate] = []
        seen_chunks: set[uuid.UUID] = set()

        for c in candidates:
            if c.chunk_id not in seen_chunks:
                seen_chunks.add(c.chunk_id)
                unique_candidates.append(c)

        # Step 2: Enforce token budget on the candidates
        budgeted_candidates: list[Candidate] = []
        total_tokens = 0

        for c in unique_candidates:
            # Estimate tokens including XML wrapper overhead
            overhead_str = f'<source id="99" doc_id="{c.document_id}" section="{c.section_path}" pages="99-99">\n\n</source>\n'
            chunk_tokens = self.estimate_tokens(c.content + overhead_str)
            if total_tokens + chunk_tokens > max_context_tokens and budgeted_candidates:
                # Stop adding chunks once token budget is reached
                break
            budgeted_candidates.append(c)
            total_tokens += chunk_tokens

        # Step 3: Apply Lost-in-the-Middle reordering
        if enable_lost_in_middle and len(budgeted_candidates) > 2:
            ordered_candidates = self.reorder_lost_in_the_middle(budgeted_candidates)
        else:
            ordered_candidates = budgeted_candidates

        # Step 4: Assemble XML formatted context and assign 1-based IDs
        sources: list[SourceItem] = []
        source_map: dict[int, Candidate] = {}
        context_blocks: list[str] = []

        for idx, candidate in enumerate(ordered_candidates, start=1):
            source_item = SourceItem(source_id=idx, candidate=candidate)
            sources.append(source_item)
            source_map[idx] = candidate

            page_info = ""
            if candidate.page_start is not None:
                if candidate.page_end is not None and candidate.page_end != candidate.page_start:
                    page_info = f' pages="{candidate.page_start}-{candidate.page_end}"'
                else:
                    page_info = f' page="{candidate.page_start}"'

            section_attr = f' section="{candidate.section_path}"' if candidate.section_path else ""

            block = (
                f'<source id="{idx}" doc_id="{candidate.document_id}"{section_attr}{page_info}>\n'
                f"{candidate.content.strip()}\n"
                f"</source>"
            )
            context_blocks.append(block)

        full_context_text = "\n\n".join(context_blocks)
        actual_estimated_tokens = self.estimate_tokens(full_context_text)

        return BuiltContext(
            context_text=full_context_text,
            sources=sources,
            source_map=source_map,
            estimated_tokens=actual_estimated_tokens,
        )
