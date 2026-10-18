import re
from typing import Sequence
from app.rag.retrieval.base import Candidate

# Common English stopwords to ignore when measuring sentence query relevance
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

# Regex to split text into sentences using fixed-width lookbehind
SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?])\s+")


class ExtractiveSentenceCompressor:
    """
    Compresses retrieved candidate chunks by extracting query-relevant sentences
    along with their immediate surrounding sentence window (+/- window_size).
    Preserves contextual chunk headers and eliminates extraneous preamble sentences.
    """

    def __init__(self, window_size: int = 1, min_sentence_score: float = 0.15) -> None:
        self.window_size = window_size
        self.min_sentence_score = min_sentence_score

    def _extract_query_keywords(self, query: str) -> set[str]:
        words = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", query.lower())
        return {w for w in words if w not in STOPWORDS}

    def _score_sentence(self, sentence: str, query_keywords: set[str]) -> float:
        if not query_keywords:
            return 0.0

        sent_words = set(re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", sentence.lower()))
        matched = query_keywords.intersection(sent_words)
        return len(matched) / len(query_keywords)

    def compress_chunk_content(self, query: str, content: str) -> str:
        """
        Compresses single chunk content. If a contextual header [Document: ...] is present,
        it is preserved and the remaining body is compressed.
        """
        # Separate contextual header if present
        header = ""
        body = content.strip()
        if body.startswith("[Document:") and "\n\n" in body:
            header, body = body.split("\n\n", 1)
            header = header.strip() + "\n\n"

        # Split body into sentences
        raw_sentences = [s.strip() for s in SENTENCE_SPLIT_REGEX.split(body) if s.strip()]
        if len(raw_sentences) <= 2:
            return content  # Too short to safely compress without risking loss of context

        query_keywords = self._extract_query_keywords(query)
        if not query_keywords:
            return content

        # Score each sentence
        sentence_scores = [self._score_sentence(s, query_keywords) for s in raw_sentences]

        # Identify indices of focal sentences meeting threshold
        focal_indices = [
            i for i, score in enumerate(sentence_scores) if score >= self.min_sentence_score
        ]

        if not focal_indices:
            # If no sentence strictly meets threshold, pick the single highest scoring sentence
            best_idx = max(range(len(sentence_scores)), key=lambda i: sentence_scores[i])
            if sentence_scores[best_idx] > 0:
                focal_indices = [best_idx]
            else:
                return content  # Keep all if zero keyword match

        # Expand focal sentences with +/- window_size context
        selected_indices: set[int] = set()
        for idx in focal_indices:
            for offset in range(-self.window_size, self.window_size + 1):
                target = idx + offset
                if 0 <= target < len(raw_sentences):
                    selected_indices.add(target)

        # If we selected almost all sentences, return original content
        if len(selected_indices) >= len(raw_sentences) - 1:
            return content

        sorted_indices = sorted(selected_indices)
        compressed_parts: list[str] = []
        last_idx = -1

        for idx in sorted_indices:
            if last_idx != -1 and idx > last_idx + 1:
                compressed_parts.append("...")
            # Restore sentence period if omitted by split
            sent = raw_sentences[idx]
            if not sent.endswith((".", "!", "?")):
                sent += "."
            compressed_parts.append(sent)
            last_idx = idx

        compressed_body = " ".join(compressed_parts)
        return f"{header}{compressed_body}".strip()

    def compress(
        self,
        query: str,
        candidates: Sequence[Candidate],
    ) -> list[Candidate]:
        """Compresses all candidates in place, returning modified Candidate objects."""
        compressed_candidates: list[Candidate] = []

        for c in candidates:
            compressed_text = self.compress_chunk_content(query, c.content)
            is_modified = len(compressed_text) < len(c.content)

            compressed_candidates.append(
                Candidate(
                    chunk_id=c.chunk_id,
                    document_id=c.document_id,
                    collection_id=c.collection_id,
                    content=compressed_text,
                    section_path=c.section_path,
                    page_start=c.page_start,
                    page_end=c.page_end,
                    score=c.score,
                    retrieval_method=c.retrieval_method,
                    metadata={
                        **c.metadata,
                        "compressed": is_modified,
                        "original_length": len(c.content),
                        "compressed_length": len(compressed_text),
                    },
                )
            )

        return compressed_candidates
