from app.rag.parsing.base import BaseParser, Element
from app.rag.parsing.pdf import PDFParser
from app.rag.parsing.markdown import MarkdownParser


class PlainTextParser:
    def parse(self, content: bytes, filename: str) -> list[Element]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="replace")

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return [
            Element(type="paragraph", text=p, page_number=1, heading_path=filename)
            for p in paragraphs
        ]


class ParserRegistry:
    def __init__(self):
        self._parsers: dict[str, BaseParser] = {
            "application/pdf": PDFParser(),
            ".pdf": PDFParser(),
            "text/markdown": MarkdownParser(),
            ".md": MarkdownParser(),
            "text/plain": PlainTextParser(),
            ".txt": PlainTextParser(),
        }

    def get_parser(self, mime_type: str, filename: str) -> BaseParser:
        if mime_type in self._parsers:
            return self._parsers[mime_type]

        # Fallback to extension check
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext in self._parsers:
            return self._parsers[ext]

        raise ValueError(f"Unsupported file format: {mime_type} ({filename})")


parser_registry = ParserRegistry()
