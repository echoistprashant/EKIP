from app.rag.chunking.structural import StructuralChunker
from app.rag.parsing.base import Element
from app.rag.parsing.markdown import MarkdownParser


def test_structural_chunker_adds_contextual_headers():
    doc_title = "Global Travel & Expense Policy"
    md_content = """# North America Policy
## Travel Allowances
Employees can claim $150 per day for meals during domestic business trips. Receipts are required.

## Car Rental
Economy cars must be booked through the company portal. Upgrades require director approval.
""".encode("utf-8")

    parser = MarkdownParser()
    elements = parser.parse(md_content, "travel_policy.md")

    chunker = StructuralChunker(max_tokens=400, overlap_tokens=50)
    chunks = chunker.chunk(elements, doc_title=doc_title)

    assert len(chunks) >= 2

    # Check first chunk has Contextual Header
    first_chunk = chunks[0]
    assert "[Document: Global Travel & Expense Policy" in first_chunk.content
    assert "Section: North America Policy > Travel Allowances" in first_chunk.content
    assert "$150 per day" in first_chunk.content
    assert first_chunk.ordinal == 0

    # Check second chunk
    second_chunk = chunks[1]
    assert "Section: North America Policy > Car Rental" in second_chunk.content
    assert "Economy cars" in second_chunk.content
    assert second_chunk.ordinal == 1


def test_structural_chunker_preserves_table():
    doc_title = "HR Policy"
    elements = [
        Element(
            type="table",
            text="| Leave Type | Days Allowed |\n| --- | --- |\n| Sick Leave | 12 days |\n| Casual Leave | 10 days |",
            page_number=3,
            heading_path="Leaves > Paid Time Off",
        )
    ]

    chunker = StructuralChunker(max_tokens=400, overlap_tokens=50)
    chunks = chunker.chunk(elements, doc_title=doc_title)

    assert len(chunks) == 1
    table_chunk = chunks[0]
    assert "| Leave Type | Days Allowed |" in table_chunk.content
    assert "Sick Leave | 12 days" in table_chunk.content
    assert table_chunk.page_start == 3
    assert table_chunk.page_end == 3
    assert "[Document: HR Policy | Section: Leaves > Paid Time Off]" in table_chunk.content
