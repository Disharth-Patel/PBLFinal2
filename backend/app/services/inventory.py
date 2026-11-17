from pathlib import Path

import fitz
import openpyxl
from docx import Document
from pptx import Presentation

from app.schemas import SourceDocument


SUPPORTED_FILES = {".pdf", ".xlsx", ".docx", ".pptx", ".csv", ".txt"}


def build_source_inventory(source_directory: Path) -> list[SourceDocument]:
    records: list[SourceDocument] = []
    for path in sorted(source_directory.iterdir()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_FILES:
            continue
        if path.suffix.lower() == ".pdf":
            records.append(_inspect_pdf(path))
        elif path.suffix.lower() == ".xlsx":
            records.append(_inspect_xlsx(path))
        else:
            records.append(_inspect_textual(path))
    return records


def _inspect_pdf(path: Path) -> SourceDocument:
    with fitz.open(path) as document:
        text = "\n".join(page.get_text() for page in document)
        pages = len(document)
    return SourceDocument(
        filename=path.name,
        format="PDF",
        size_bytes=path.stat().st_size,
        pages_or_sheets=pages,
        extracted_characters=len(text),
        extraction_status="text-extracted" if text.strip() else "ocr-required",
        path=str(path),
    )


def _inspect_xlsx(path: Path) -> SourceDocument:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet_count = len(workbook.sheetnames)
        rows = sum(sheet.max_row for sheet in workbook.worksheets)
    finally:
        workbook.close()
    return SourceDocument(
        filename=path.name,
        format="XLSX",
        size_bytes=path.stat().st_size,
        pages_or_sheets=sheet_count,
        extracted_characters=rows,
        extraction_status="structured-data-extracted",
        path=str(path),
    )


def _inspect_textual(path: Path) -> SourceDocument:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        document = Document(path)
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        records = len(document.paragraphs)
    elif suffix == ".pptx":
        presentation = Presentation(path)
        text = "\n".join(
            shape.text
            for slide in presentation.slides
            for shape in slide.shapes
            if hasattr(shape, "text")
        )
        records = len(presentation.slides)
    else:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        records = 1
    return SourceDocument(
        filename=path.name,
        format=suffix[1:].upper(),
        size_bytes=path.stat().st_size,
        pages_or_sheets=records,
        extracted_characters=len(text),
        extraction_status="text-extracted" if text.strip() else "empty",
        path=str(path),
    )
