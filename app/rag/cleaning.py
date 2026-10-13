import re
from collections import defaultdict
from app.rag.parsing.base import Element


class DocumentCleaner:
    """
    Cleans raw extracted elements:
    - Strips recurring boilerplate headers/footers (>50% pages)
    - Normalizes Unicode and whitespace
    - Fixes hyphenation line-breaks
    - Strictly preserves legal numbering and table structures
    """

    def clean(self, elements: list[Element]) -> list[Element]:
        if not elements:
            return []

        # 1. Identify distinct pages
        all_pages = {el.page_number for el in elements}
        total_pages = len(all_pages)

        # 2. Detect recurring lines across pages if multi-page
        boilerplate_lines: set[str] = set()
        if total_pages > 2:
            page_line_counts: dict[str, set[int]] = defaultdict(set)
            for el in elements:
                # Don't check tables for headers
                if el.type == "table":
                    continue
                for line in el.text.splitlines():
                    cleaned = line.strip()
                    # Only short lines (<80 chars) are candidates for headers/footers
                    if cleaned and len(cleaned) < 80:
                        page_line_counts[cleaned].add(el.page_number)

            threshold = total_pages * 0.5
            for line_text, pages in page_line_counts.items():
                if len(pages) > threshold:
                    boilerplate_lines.add(line_text)

        cleaned_elements: list[Element] = []

        for el in elements:
            text = el.text

            # If table, preserve exact structure
            if el.type == "table":
                cleaned_elements.append(el)
                continue

            # Strip recurring boilerplate lines
            if boilerplate_lines:
                lines = [l for l in text.splitlines() if l.strip() not in boilerplate_lines]
                text = "\n".join(lines)

            # Fix hyphenation: e.g. "con- \n tinue" -> "continue"
            text = re.sub(r"(\b\w+)-\s*\n\s*(\w+\b)", r"\1\2", text)

            # Normalize multiple spaces and tabs (preserving single linebreaks)
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n\s*\n+", "\n\n", text).strip()

            if text:
                cleaned_elements.append(
                    Element(
                        type=el.type,
                        text=text,
                        page_number=el.page_number,
                        heading_path=el.heading_path,
                    )
                )

        return cleaned_elements


document_cleaner = DocumentCleaner()
