from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pymupdf


class DocumentProcessingError(ValueError):
    """The uploaded document could not be opened or rendered safely."""


@dataclass(frozen=True)
class RasterizedPage:
    page_number: int
    path: Path
    width: int
    height: int


def rasterize_document(
    source: Path,
    output_directory: Path,
    dpi: int = 150,
    progress: Callable[[int, int], None] | None = None,
) -> list[RasterizedPage]:
    """Render a PDF, PNG, or JPEG file into standardized JPEG page images."""
    if dpi <= 0:
        raise ValueError("dpi must be greater than zero")

    output_directory.mkdir(parents=True, exist_ok=True)
    try:
        document = pymupdf.open(source)
    except (pymupdf.FileDataError, RuntimeError, OSError) as exc:
        raise DocumentProcessingError("The uploaded file is not a readable PDF or image.") from exc

    try:
        if document.page_count < 1:
            raise DocumentProcessingError("The uploaded document does not contain any pages.")

        pages: list[RasterizedPage] = []
        total_pages = document.page_count
        for zero_indexed_page in range(total_pages):
            page = document.load_page(zero_indexed_page)
            pixmap = page.get_pixmap(dpi=dpi, alpha=False)
            image_path = output_directory / f"page-{zero_indexed_page + 1:04d}.jpg"
            pixmap.save(image_path)
            pages.append(
                RasterizedPage(
                    page_number=zero_indexed_page + 1,
                    path=image_path,
                    width=pixmap.width,
                    height=pixmap.height,
                )
            )
            if progress is not None:
                progress(zero_indexed_page + 1, total_pages)
        return pages
    finally:
        document.close()
