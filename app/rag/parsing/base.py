from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass
class Element:
    """Represents an atomic, structured content element extracted from a document."""
    type: Literal["heading", "paragraph", "table", "list"]
    text: str
    page_number: int
    heading_path: str = ""


class BaseParser(Protocol):
    """Protocol for document format parsers."""
    def parse(self, content: bytes, filename: str) -> list[Element]:
        ...
