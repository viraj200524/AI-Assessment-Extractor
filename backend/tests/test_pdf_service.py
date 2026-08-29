from pathlib import Path

import pymupdf

from app.services.pdf_service import rasterize_document


def test_rasterize_pdf_preserves_page_order_and_emits_jpegs(tmp_path: Path) -> None:
    source = tmp_path / "paper.pdf"
    document = pymupdf.open()
    for text in ("Question 1", "Question 2"):
        page = document.new_page()
        page.insert_text((72, 72), text)
    document.save(source)
    document.close()

    pages = rasterize_document(source, tmp_path / "rendered", dpi=150)

    assert [page.page_number for page in pages] == [1, 2]
    assert all(page.path.suffix == ".jpg" and page.path.exists() for page in pages)
    assert all(page.width > 0 and page.height > 0 for page in pages)
