import json
from pathlib import Path

import fitz
import openpyxl
from docx import Document
from pptx import Presentation

from app.schemas import ExtractionResult


def extract_source_documents(
    source_directory: Path, output_directory: Path
) -> list[ExtractionResult]:
    output_directory.mkdir(parents=True, exist_ok=True)
    results: list[ExtractionResult] = []
    for source_path in sorted(
        source_directory.iterdir(),
        key=lambda path: (path.stem.lower(), path.suffix.lower() == ".json", path.name.lower()),
    ):
        if not source_path.is_file():
            continue
        if source_path.suffix.lower() not in {".pdf", ".xlsx", ".docx", ".pptx", ".csv", ".txt", ".json"}:
            continue
        results.append(extract_document(source_path, output_directory))
    return results


def extract_document(source_path: Path, output_directory: Path) -> ExtractionResult:
    output_directory.mkdir(parents=True, exist_ok=True)
    suffix = source_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(source_path, output_directory)
    if suffix == ".xlsx":
        return _extract_xlsx(source_path, output_directory)
    if suffix == ".docx":
        return _extract_docx(source_path, output_directory)
    if suffix == ".pptx":
        return _extract_pptx(source_path, output_directory)
    if suffix == ".json":
        return _extract_json(source_path, output_directory)
    if suffix in {".csv", ".txt"}:
        return _extract_text_file(source_path, output_directory)
    raise ValueError(f"Unsupported document type: {source_path.suffix}")


def _extract_pdf(source_path: Path, output_directory: Path) -> ExtractionResult:
    pages: list[dict[str, int | str]] = []
    with fitz.open(source_path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text().strip()
            if text:
                pages.append({"page": page_number, "text": text})
    output_path = output_directory / f"{source_path.stem}.json"
    _write_json(output_path, {"source": source_path.name, "format": "PDF", "pages": pages})
    return ExtractionResult(
        filename=source_path.name,
        output_path=str(output_path),
        records=len(pages),
        extracted_characters=sum(len(page["text"]) for page in pages),
        status="text-extracted" if pages else "ocr-required",
    )


def _extract_xlsx(source_path: Path, output_directory: Path) -> ExtractionResult:
    workbook = openpyxl.load_workbook(source_path, read_only=True, data_only=True)
    sheets: list[dict[str, object]] = []
    try:
        for worksheet in workbook.worksheets:
            rows = [
                [cell for cell in row]
                for row in worksheet.iter_rows(values_only=True)
            ]
            sheets.append({"name": worksheet.title, "rows": rows})
    finally:
        workbook.close()
    output_path = output_directory / f"{source_path.stem}.json"
    _write_json(output_path, {"source": source_path.name, "format": "XLSX", "sheets": sheets})
    row_count = sum(len(sheet["rows"]) for sheet in sheets)
    return ExtractionResult(
        filename=source_path.name,
        output_path=str(output_path),
        records=row_count,
        extracted_characters=sum(len(str(cell)) for sheet in sheets for row in sheet["rows"] for cell in row if cell is not None),
        status="structured-data-extracted",
    )


def _extract_docx(source_path: Path, output_directory: Path) -> ExtractionResult:
    document = Document(source_path)
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    output_path = output_directory / f"{source_path.stem}.json"
    _write_json(output_path, {"source": source_path.name, "format": "DOCX", "paragraphs": paragraphs})
    return ExtractionResult(
        filename=source_path.name,
        output_path=str(output_path),
        records=len(paragraphs),
        extracted_characters=sum(len(text) for text in paragraphs),
        status="text-extracted" if paragraphs else "empty",
    )


def _extract_pptx(source_path: Path, output_directory: Path) -> ExtractionResult:
    presentation = Presentation(source_path)
    slides: list[dict[str, object]] = []
    for slide_number, slide in enumerate(presentation.slides, start=1):
        text = "\n".join(shape.text.strip() for shape in slide.shapes if hasattr(shape, "text") and shape.text.strip())
        if text:
            slides.append({"slide": slide_number, "text": text})
    output_path = output_directory / f"{source_path.stem}.json"
    _write_json(output_path, {"source": source_path.name, "format": "PPTX", "slides": slides})
    return ExtractionResult(
        filename=source_path.name,
        output_path=str(output_path),
        records=len(slides),
        extracted_characters=sum(len(slide["text"]) for slide in slides),
        status="text-extracted" if slides else "empty",
    )


def _extract_text_file(source_path: Path, output_directory: Path) -> ExtractionResult:
    text = source_path.read_text(encoding="utf-8-sig", errors="replace").strip()
    output_path = output_directory / f"{source_path.stem}.json"
    _write_json(output_path, {"source": source_path.name, "format": source_path.suffix[1:].upper(), "text": text})
    return ExtractionResult(
        filename=source_path.name,
        output_path=str(output_path),
        records=1 if text else 0,
        extracted_characters=len(text),
        status="text-extracted" if text else "empty",
    )


def _extract_json(source_path: Path, output_directory: Path) -> ExtractionResult:
    payload = json.loads(source_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON source must contain an object: {source_path.name}")
    output_path = output_directory / f"{source_path.stem}.json-source.json"
    _write_json(output_path, {"source": source_path.name, "format": "JSON", "data": payload})
    records = payload.get("courses") or payload.get("records") or []
    return ExtractionResult(
        filename=source_path.name,
        output_path=str(output_path),
        records=len(records) if isinstance(records, list) else 1,
        extracted_characters=len(json.dumps(payload, ensure_ascii=False)),
        status="structured-data-extracted",
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
