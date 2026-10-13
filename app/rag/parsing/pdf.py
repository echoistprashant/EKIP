import io
import re
from pypdf import PdfReader
from app.rag.parsing.base import Element


class PDFParser:
    """Extracts structured elements and page numbers from PDF files."""

    def parse(self, content: bytes, filename: str) -> list[Element]:
        try:
            reader = PdfReader(io.BytesIO(content))
        except Exception as e:
            raise ValueError(f"Failed to read PDF file: {e}") from e

        if len(reader.pages) == 0:
            raise ValueError("PDF file contains no pages")

        elements: list[Element] = []
        current_heading_path: list[str] = []

        for page_idx, page in enumerate(reader.pages):
            page_num = page_idx + 1
            raw_text = page.extract_text() or ""
            lines = raw_text.splitlines()

            current_paragraph_lines: list[str] = []

            for line in lines:
                cleaned_line = line.strip()
                if not cleaned_line:
                    if current_paragraph_lines:
                        para_text = " ".join(current_paragraph_lines)
                        elements.append(
                            Element(
                                type="paragraph",
                                text=para_text,
                                page_number=page_num,
                                heading_path=" > ".join(current_heading_path),
                            )
                        )
                        current_paragraph_lines = []
                    continue

                # Heuristic for Headings:
                # 1. Matches "Section 1", "1.1", "Article IV", or ALL CAPS short lines (<60 chars)
                is_numbered_heading = bool(re.match(r"^(\d+(\.\d+)*|[A-Z]\.|\bSection\b|\bArticle\b)", cleaned_line, re.IGNORECASE))
                is_short_title = len(cleaned_line) < 60 and not cleaned_line.endswith((".", ":", ";", ","))

                if (is_numbered_heading or cleaned_line.isupper()) and is_short_title:
                    # Flush pending paragraph
                    if current_paragraph_lines:
                        elements.append(
                            Element(
                                type="paragraph",
                                text=" ".join(current_paragraph_lines),
                                page_number=page_num,
                                heading_path=" > ".join(current_heading_path),
                            )
                        )
                        current_paragraph_lines = []

                    # Update heading path hierarchy
                    current_heading_path = [cleaned_line]
                    elements.append(
                        Element(
                            type="heading",
                            text=cleaned_line,
                            page_number=page_num,
                            heading_path=cleaned_line,
                        )
                    )
                else:
                    current_paragraph_lines.append(cleaned_line)

            # Flush remaining lines on page
            if current_paragraph_lines:
                elements.append(
                    Element(
                        type="paragraph",
                        text=" ".join(current_paragraph_lines),
                        page_number=page_num,
                        heading_path=" > ".join(current_heading_path),
                    )
                )

        if not elements:
            raise ValueError("No extractable text found in PDF (might be scanned or empty)")

        return elements
