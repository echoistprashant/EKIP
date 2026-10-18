from pathlib import Path
from app.llm.client import ChatMessage

PROMPTS_DIR = Path(__file__).parent

ABSTENTION_PHRASES = [
    "i do not have enough information",
    "not enough information in the provided documents",
    "insufficient evidence",
    "the provided documents do not contain",
    "i cannot answer this question based on the provided",
]


class PromptManager:
    """Manages versioned system prompts and prompt assembly."""

    def __init__(self, default_version: str = "v1") -> None:
        self.default_version = default_version
        self._cache: dict[str, str] = {}

    def get_system_prompt(self, version: str | None = None) -> str:
        ver = version or self.default_version
        if ver in self._cache:
            return self._cache[ver]

        prompt_file = PROMPTS_DIR / ver / "system.md"
        if not prompt_file.exists():
            raise FileNotFoundError(f"System prompt template not found for version '{ver}' at {prompt_file}")

        text = prompt_file.read_text(encoding="utf-8").strip()
        self._cache[ver] = text
        return text

    def format_messages(
        self,
        context_text: str,
        question: str,
        version: str | None = None,
    ) -> tuple[list[ChatMessage], str]:
        """
        Builds ChatMessage list with versioned system prompt and structured user prompt.
        Returns: (messages, version_used)
        """
        ver = version or self.default_version
        system_content = self.get_system_prompt(ver)

        user_content = (
            f"<context>\n"
            f"{context_text}\n"
            f"</context>\n\n"
            f"<question>\n"
            f"{question.strip()}\n"
            f"</question>"
        )

        messages = [
            ChatMessage(role="system", content=system_content),
            ChatMessage(role="user", content=user_content),
        ]
        return messages, ver

    @staticmethod
    def is_abstention(answer: str) -> bool:
        """Determines if the generated answer indicates insufficient information / refusal."""
        cleaned = answer.strip().lower()
        if not cleaned:
            return True
        return any(phrase in cleaned for phrase in ABSTENTION_PHRASES)
