from pathlib import Path

from app.services.inventory import build_source_inventory


def test_source_inventory_detects_all_initial_documents() -> None:
    records = build_source_inventory(Path(__file__).resolve().parents[2])

    assert [record.filename for record in records] == [
        "Final SOC Brochure 2026_cmp.pdf",
        "institution_contact_directory.xlsx",
        "MIT_ADT_University_Fees_2026-27.xlsx",
        "MITID_Admissions_Brochure_2027-28.pdf",
        "SAP_Brochure 2026.pdf",
    ]
    assert records[0].extraction_status == "ocr-required"
    assert records[1].extraction_status == "structured-data-extracted"
    assert records[2].extraction_status == "structured-data-extracted"
    assert records[4].extraction_status == "text-extracted"
