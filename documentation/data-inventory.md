# Institutional data inventory

Inventory date: 2026-11-10

The project source files are retained unchanged in the project root. Generated
extractions are stored under `data/extracted`.

| Filename | Format | Category | Observed content | Extraction status |
|---|---|---|---|---|
| `SAP_Brochure 2026.pdf` | PDF, 35 pages | Programmes, campus, institutional information | MIT ADT University overview, architecture/planning and other programme material | Text extraction works; 51,492 characters extracted |
| `Final SOC Brochure 2026_cmp.pdf` | PDF, 104 pages | School of Computing programmes | Likely programme and admissions brochure based on filename | PDF pages are image/scanned content; text extraction returned no usable text and requires OCR |
| `MITID_Admissions_Brochure_2027-28.pdf` | PDF, 4 pages | Admissions and design programmes | Admissions brochure based on filename | PDF pages are image/scanned content; text extraction returned no usable text and requires OCR |
| `institution_contact_directory.xlsx` | XLSX, 1 sheet, 20 data rows | Institutional contacts | School/institute, contact person and contact number directory | Extraction works with `openpyxl` |
| `MIT_ADT_University_Fees_2026-27.xlsx` | XLSX, 3 sheets, 45 course rows | Course fees and additional charges | Year-wise course fees for 2026-27 through 2029-30, plus hostel/mess and other charges | Extraction works with `openpyxl`; fee headers are preserved during RAG indexing |

## Verified spreadsheet information

The workbook contains a `Contact Directory` sheet with 20 institutional contact
records. The extracted columns are:

- Institution / School
- Contact Person(s)
- Contact Number(s)

The workbook is suitable for structured knowledge-base ingestion after validating
phone-number privacy and administrator access rules.

The fee workbook is indexed as structured fee content. Blank year-wise values mean
that no figure was supplied, not zero. The workbook itself states that some charges
may be excluded and that amounts should be confirmed against the official fee page
before payment or admission decisions.

## Missing or unresolved information

- The two scanned PDFs require a local OCR step before their programme, eligibility,
  fee and deadline information can be safely indexed.
- The fee workbook provides a year-wise fee schedule, but it is a compiled data
  source rather than a replacement for the university's official fee page.
- No source file was found that can yet be treated as a complete authoritative
  scholarship schedule or admission deadline register.
- Conflicting values cannot be assessed until OCR extraction is completed and documents
  are normalized into comparable records.

The assistant must refuse to present unavailable fees, deadlines, eligibility rules or
other unverified facts as institutional truth.

## Local Ollama availability

The local Ollama endpoint at `http://localhost:11434` responded during inventory:

- `all-minilm:latest` — local embedding model
- `qwen2.5:1.5b-instruct` — local generation model
- `llama3.2:latest` — local generation model
- `glm-5.1:cloud` — remote model entry; it must be excluded from this application's
  selectable models because the project requires local-only inference
