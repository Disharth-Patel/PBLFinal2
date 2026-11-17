import json
from pathlib import Path

from app.services.extraction import extract_document, extract_source_documents


def test_extracts_pdf_pages_and_spreadsheet_rows(tmp_path: Path) -> None:
    source_directory = Path(__file__).resolve().parents[2]
    output_directory = tmp_path / "extracted"

    results = extract_source_documents(source_directory, output_directory)

    assert {result.filename for result in results} == {
        "Final SOC Brochure 2026_cmp.pdf",
        "institution_contact_directory.xlsx",
        "MIT_ADT_University_Fees_2026-27.json",
        "MIT_ADT_University_Fees_2026-27.xlsx",
        "MITID_Admissions_Brochure_2027-28.pdf",
        "SAP_Brochure 2026.pdf",
    }
    workbook_output = output_directory / "institution_contact_directory.json"
    payload = json.loads(workbook_output.read_text(encoding="utf-8"))
    assert payload["sheets"][0]["name"] == "Contact Directory"
    assert payload["sheets"][0]["rows"][1][1] == "Institution / School"
    fees_output = output_directory / "MIT_ADT_University_Fees_2026-27.json"
    fees_payload = json.loads(fees_output.read_text(encoding="utf-8"))
    assert fees_payload["sheets"][0]["rows"][1][1] == "Aerospace Engineering"


def test_extract_document_processes_uploaded_text_file(tmp_path: Path) -> None:
    source = tmp_path / "uploaded.txt"
    output = tmp_path / "extracted"
    source.write_text("Admissions information", encoding="utf-8")

    result = extract_document(source, output)

    assert result.status == "text-extracted"
    assert json.loads((output / "uploaded.json").read_text(encoding="utf-8"))["text"] == "Admissions information"


def test_extract_document_processes_structured_fee_json(tmp_path: Path) -> None:
    source = tmp_path / "fees.json"
    output = tmp_path / "extracted"
    source.write_text(
        json.dumps({"courses": [{"course": "Aerospace Engineering", "total_fees_inr": 1060000}]}),
        encoding="utf-8",
    )

    result = extract_document(source, output)

    assert result.status == "structured-data-extracted"
    payload = json.loads((output / "fees.json-source.json").read_text(encoding="utf-8"))
    assert payload["format"] == "JSON"
    assert payload["data"]["courses"][0]["course"] == "Aerospace Engineering"
