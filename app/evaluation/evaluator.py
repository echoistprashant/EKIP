import re
from typing import Sequence

from app.cache.base import compute_cosine_similarity
from app.evaluation.models import TriadEvaluationResult
from app.rag.embeddings.base import BaseEmbedder

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

ABSTENTION_MARKERS = [
    "not have enough information",
    "insufficient evidence",
    "provided documents do not contain",
    "cannot answer this question",
]


class RAGTriadEvaluator:
    """
    100% Free, local CPU evaluator for the RAG Triad:
    1. Context Relevance: How relevant is the retrieved context to the query?
    2. Groundedness (Faithfulness): Are all claims supported by the context without hallucination?
    3. Answer Relevance: Does the generated response directly answer the query?
    """

    def __init__(
        self,
        embedder: BaseEmbedder | None = None,
        min_groundedness_threshold: float = 0.50,
        min_answer_relevance_threshold: float = 0.50,
    ) -> None:
        self.embedder = embedder
        self.min_groundedness_threshold = min_groundedness_threshold
        self.min_answer_relevance_threshold = min_answer_relevance_threshold

    def _extract_keywords(self, text: str) -> list[str]:
        words = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", text.lower())
        return [w for w in words if w not in STOPWORDS]

    def _split_sentences(self, text: str) -> list[str]:
        # Strip bracket citations before splitting
        clean_text = re.sub(r"\[\d+(?:\s*,\s*\d+)*\]", "", text)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text) if s.strip()]
        return sentences

    def _word_matches(self, word: str, text: str) -> bool:
        if word in text:
            return True
        if word.endswith("s") and word[:-1] in text:
            return True
        if len(word) >= 5:
            stem = word[: len(word) - 3]
            if len(stem) >= 3 and stem in text:
                return True
        return False

    def evaluate_context_relevance(self, query: str, context: str) -> float:
        """Evaluates whether retrieved context covers query keywords."""
        query_kw = self._extract_keywords(query)
        if not query_kw:
            return 1.0

        context_lower = context.lower()
        matched = sum(1 for kw in query_kw if self._word_matches(kw, context_lower))
        score = matched / len(query_kw)
        return min(1.0, max(0.0, round(score, 3)))

    def evaluate_groundedness(self, answer: str, context: str) -> tuple[float, list[str]]:
        """
        Decomposes answer into sentences and verifies that each claim
        has lexical grounding in the provided context.
        """
        # If model abstained, it is 100% faithful / grounded (0 hallucination)
        if any(marker in answer.lower() for marker in ABSTENTION_MARKERS):
            return 1.0, []

        sentences = self._split_sentences(answer)
        if not sentences:
            return 1.0, []

        context_lower = context.lower()
        unsupported: list[str] = []
        grounded_count = 0

        for sent in sentences:
            sent_kw = self._extract_keywords(sent)
            if not sent_kw:
                grounded_count += 1
                continue

            # Check keyword support ratio in context
            matched_kw = sum(1 for kw in sent_kw if kw in context_lower)
            support_ratio = matched_kw / len(sent_kw)

            # Claim is grounded if at least 30% of content words are present in context
            if support_ratio >= 0.30:
                grounded_count += 1
            else:
                unsupported.append(sent)

        score = grounded_count / len(sentences)
        return min(1.0, max(0.0, round(score, 3))), unsupported

    def evaluate_answer_relevance(self, query: str, answer: str) -> float:
        """Evaluates if the answer addresses the query."""
        if any(marker in answer.lower() for marker in ABSTENTION_MARKERS):
            return 1.0

        query_kw = self._extract_keywords(query)
        if not query_kw:
            return 1.0

        answer_lower = answer.lower()
        matched = sum(1 for kw in query_kw if kw in answer_lower)
        score = matched / len(query_kw)
        # Give a small base score if answer has substantive length
        base_bonus = 0.2 if len(answer.split()) >= 5 else 0.0
        final_score = min(1.0, max(0.0, (score * 0.8) + base_bonus))
        return round(final_score, 3)

    async def evaluate(
        self,
        query: str,
        context: str,
        answer: str,
    ) -> TriadEvaluationResult:
        """
        Executes full RAG Triad evaluation.
        Computes Context Relevance, Groundedness, and Answer Relevance.
        Applies guardrails for hallucination detection.
        """
        ctx_rel = self.evaluate_context_relevance(query, context)
        groundedness, unsupported = self.evaluate_groundedness(answer, context)
        ans_rel = self.evaluate_answer_relevance(query, answer)

        # Composite RAG Triad score
        composite = round((ctx_rel + groundedness + ans_rel) / 3.0, 3)

        # Guardrail checks
        hallucination_warning = groundedness < self.min_groundedness_threshold
        passed_guardrails = (
            groundedness >= self.min_groundedness_threshold
            and ans_rel >= self.min_answer_relevance_threshold
        )

        verdict = "PASS"
        if hallucination_warning:
            verdict = "HALLUCINATION_DETECTED"
        elif not passed_guardrails:
            verdict = "LOW_RELEVANCE"

        return TriadEvaluationResult(
            context_relevance=ctx_rel,
            groundedness=groundedness,
            answer_relevance=ans_rel,
            rag_triad_score=composite,
            passed_guardrails=passed_guardrails,
            hallucination_warning=hallucination_warning,
            unsupported_claims=unsupported,
            verdict=verdict,
            details={
                "unsupported_claim_count": len(unsupported),
                "sentence_count": len(self._split_sentences(answer)),
            },
        )
