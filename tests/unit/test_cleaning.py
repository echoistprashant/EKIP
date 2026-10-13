from app.rag.cleaning import DocumentCleaner
from app.rag.parsing.base import Element


def test_cleaner_removes_recurring_headers_across_pages():
    cleaner = DocumentCleaner()

    # Create 4 pages with recurring header "Acme Corp Confidential"
    elements = [
        Element(type="paragraph", text="Acme Corp Confidential\nFirst page content of policy.", page_number=1),
        Element(type="paragraph", text="Acme Corp Confidential\nSecond page content of policy.", page_number=2),
        Element(type="paragraph", text="Acme Corp Confidential\nThird page content of policy.", page_number=3),
        Element(type="paragraph", text="Section 4.1 Unique content without header.", page_number=4),
    ]

    cleaned = cleaner.clean(elements)

    assert len(cleaned) == 4
    # "Acme Corp Confidential" appeared on 3 out of 4 pages (>50%) -> should be stripped
    for el in cleaned[:3]:
        assert "Acme Corp Confidential" not in el.text

    # Unique content preserved
    assert "First page content" in cleaned[0].text
    assert "Second page content" in cleaned[1].text
    assert "Section 4.1 Unique content" in cleaned[3].text


def test_cleaner_preserves_legal_numbering():
    cleaner = DocumentCleaner()
    elements = [
        Element(type="paragraph", text="1.1.2 The contractor shall comply with all safety regulations.", page_number=1),
    ]

    cleaned = cleaner.clean(elements)
    assert len(cleaned) == 1
    assert "1.1.2 The contractor shall comply" in cleaned[0].text
