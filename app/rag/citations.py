import re
from dataclasses import dataclass
from typing import Sequence
import uuid

from app.rag.retrieval.base import Candidate
from app.schemas.query import CitationItem

# Regex to detect bracketed citations: e.g. [1], [2], [1, 2], [1][2]
CITATION_REGEX = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had",
    "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd",
    "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
    "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off",
    "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over",
    "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd",
    "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
    "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
}


@dataclass
class CitationVerificationResult:
    """Detailed summary of extracted and validated citations."""
    citations: list[CitationItem]
    cited_source_ids: list[int]
    invalid_source_ids: list[int]
    unsupported_source_ids: list[int]
    grounding_score: float


class CitationVerifier:
    """
    Extracts citation markers from LLM answers, verifies that cited source IDs exist
    in context, and validates lexical grounding against the cited source chunks.
    """

    def extract_source_ids(self, text: str) -> list[int]:
        """Extracts unique source integer IDs in order of first appearance."""
        ids: list[int] = []
        for match in CITATION_REGEX.finditer(text):
            parts = match.group(1).split(",")
            for part in parts:
                cleaned = part.strip()
                if cleaned.isdigit():
                    sid = int(cleaned)
                    if sid not in ids:
                        ids.append(sid)
        return ids

    def verify(
        self,
        answer: str,
        source_map: dict[int, Candidate],
    ) -> CitationVerificationResult:
        """
        Validates all citations in the generated answer against available source chunks.
        """
        cited_ids = self.extract_source_ids(answer)
        if not cited_ids:
            return CitationVerificationResult(
                citations=[],
                cited_source_ids=[],
                invalid_source_ids=[],
                unsupported_source_ids=[],
                grounding_score=1.0 if not source_map else 0.0,
            )

        valid_citations: list[CitationItem] = []
        invalid_ids: list[int] = []
        unsupported_ids: list[int] = []

        # Split into sentences for per-sentence lexical verification
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer) if s.strip()]

        for sid in cited_ids:
            if sid not in source_map:
                invalid_ids.append(sid)
                continue

            candidate = source_map[sid]
            chunk_text_lower = candidate.content.lower()

            # Find sentences citing this specific sid
            claim_sentences = [
                s for s in sentences if re.search(rf"\[\s*{sid}\s*\]|\[[^\]]*,\s*{sid}\s*\]|\[\s*{sid}\s*,[^\]]*\]", s)
            ]

            # Grounding check: verify that non-stopword tokens from the sentence appear in the chunk
            has_lexical_grounding = False
            for sentence in claim_sentences:
                words = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", sentence.lower())
                keywords = [w for w in words if w not in STOPWORDS]
                if not keywords:
                    has_lexical_grounding = True
                    break

                matched_keywords = [w for w in keywords if w in chunk_text_lower]
                overlap_ratio = len(matched_keywords) / len(keywords)
                # If at least 25% of content words match the cited chunk, consider grounded
                if overlap_ratio >= 0.25:
                    has_lexical_grounding = True
                    break

            if not has_lexical_grounding and claim_sentences:
                unsupported_ids.append(sid)

            # Build CitationItem
            snippet_text = candidate.content[:180].strip()
            if len(candidate.content) > 180:
                snippet_text += "..."

            valid_citations.append(
                CitationItem(
                    source_id=sid,
                    chunk_id=candidate.chunk_id,
                    document_id=candidate.document_id,
                    section_path=candidate.section_path,
                    page_start=candidate.page_start,
                    page_end=candidate.page_end,
                    snippet=snippet_text,
                    relevance_score=round(float(candidate.score), 4),
                )
            )

        total_cited = len(cited_ids)
        verified_count = len(valid_citations) - len(unsupported_ids)
        grounding_score = max(0.0, round(verified_count / total_cited, 4)) if total_cited > 0 else 1.0

        return CitationVerificationResult(
            citations=valid_citations,
            cited_source_ids=cited_ids,
            invalid_source_ids=invalid_ids,
            unsupported_source_ids=unsupported_ids,
            grounding_score=grounding_score,
        )
