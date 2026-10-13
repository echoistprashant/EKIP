import re
from app.rag.parsing.base import Element


class MarkdownParser:
    """Parses Markdown text into structured elements with hierarchical heading paths."""

    def parse(self, content: bytes, filename: str) -> list[Element]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="replace")

        lines = text.splitlines()
        elements: list[Element] = []
        heading_stack: list[tuple[int, str]] = []  # (level, title)

        current_paragraph: list[str] = []
        in_table = False
        table_lines: list[str] = []

        def get_current_heading_path() -> str:
            return " > ".join(title for _, title in heading_stack)

        for line in lines:
            stripped = line.strip()

            # Heading check: e.g. # Heading 1, ## Heading 2
            heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if heading_match:
                # Flush pending paragraph or table
                if current_paragraph:
                    elements.append(
                        Element(
                            type="paragraph",
                            text=" ".join(current_paragraph),
                            page_number=1,
                            heading_path=get_current_heading_path(),
                        )
                    )
                    current_paragraph = []
                if table_lines:
                    elements.append(
                        Element(
                            type="table",
                            text="\n".join(table_lines),
                            page_number=1,
                            heading_path=get_current_heading_path(),
                        )
                    )
                    table_lines = []
                    in_table = False

                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()

                # Pop higher or equal level headings from stack
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, title))

                elements.append(
                    Element(
                        type="heading",
                        text=title,
                        page_number=1,
                        heading_path=get_current_heading_path(),
                    )
                )
                continue

            # Table detection (lines starting and containing '|')
            if stripped.startswith("|") and stripped.endswith("|"):
                if current_paragraph:
                    elements.append(
                        Element(
                            type="paragraph",
                            text=" ".join(current_paragraph),
                            page_number=1,
                            heading_path=get_current_heading_path(),
                        )
                    )
                    current_paragraph = []
                in_table = True
                table_lines.append(stripped)
                continue
            elif in_table:
                # Table ended
                elements.append(
                    Element(
                        type="table",
                        text="\n".join(table_lines),
                        page_number=1,
                        heading_path=get_current_heading_path(),
                    )
                )
                table_lines = []
                in_table = False

            # Regular text
            if not stripped:
                if current_paragraph:
                    elements.append(
                        Element(
                            type="paragraph",
                            text=" ".join(current_paragraph),
                            page_number=1,
                            heading_path=get_current_heading_path(),
                        )
                    )
                    current_paragraph = []
            else:
                current_paragraph.append(stripped)

        # Flush trailing content
        if table_lines:
            elements.append(
                Element(
                    type="table",
                    text="\n".join(table_lines),
                    page_number=1,
                    heading_path=get_current_heading_path(),
                )
            )
        if current_paragraph:
            elements.append(
                Element(
                    type="paragraph",
                    text=" ".join(current_paragraph),
                    page_number=1,
                    heading_path=get_current_heading_path(),
                )
            )

        return elements
