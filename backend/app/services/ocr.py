import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import fitz


def get_tesseract_executable() -> str | None:
    executable = shutil.which("tesseract")
    if executable:
        return executable
    candidate_paths = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / "tesseract.exe",
    ]
    for candidate in candidate_paths:
        if candidate.is_file():
            return str(candidate)
    return None


def capability() -> dict[str, object]:
    executable = get_tesseract_executable()
    return {
        "available": executable is not None,
        "provider": "Tesseract OCR",
        "executable": executable,
        "reason": None if executable else "Install Tesseract OCR and add it to PATH.",
    }


def ocr_pdf(path: Path, output_directory: Path) -> int:
    executable = get_tesseract_executable()
    if not executable:
        raise RuntimeError("Tesseract OCR is not installed or is not available on PATH")
    output_directory.mkdir(parents=True, exist_ok=True)
    pages = []
    with fitz.open(path) as document:
        for number, page in enumerate(document, start=1):
            with tempfile.TemporaryDirectory() as temporary:
                image_path = Path(temporary) / "page.png"
                page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(image_path)
                result = subprocess.run(
                    [executable, str(image_path), "stdout", "--psm", "6"],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                text = result.stdout.strip()
                if text:
                    pages.append({"page": number, "text": text})
    output_path = output_directory / f"{path.stem}.json"
    output_path.write_text(
        __import__("json").dumps({"source": path.name, "format": "PDF", "pages": pages}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(pages)
