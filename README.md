# AI Admissions Follow-up System

This project is being built as a local-first admissions assistant for MIT ADT University.
The original institutional files remain in the project root and are never modified.

## Current status

The application now includes the first complete end-to-end slice: persistent SQLite
accounts, student authentication, local Ollama chat grounded in extracted sources,
conversation history, lead capture, admin metrics, and a responsive React frontend.
See:

- [Data inventory](documentation/data-inventory.md)
- [Architecture roadmap](documentation/architecture-roadmap.md)

## Local backend quick start

```powershell
cd D:\PBLFinal2\backend
deactivate
Remove-Item -Recurse -Force D:\PBLFinal2\backend\.venv
python -m venv D:\PBLFinal2\backend\.venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

The service info check is available at `http://127.0.0.1:8000/`, and the API health
check is available at `http://127.0.0.1:8000/health`.

Seed local demo accounts:

```powershell
cd D:\PBLFinal2\backend
python scripts\seed_demo.py
```

Demo credentials:

- Admin: `admin@mitadt.local` / `admin-demo-123`
- Student: `student@mitadt.local` / `student-demo-123`

## Frontend

```powershell
cd D:\PBLFinal2\frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Start the backend first. The frontend calls only the
local FastAPI service, and chatbot generation calls only the local Ollama endpoint.

To extract the currently supported source files into `data/extracted`:

```powershell
Invoke-WebRequest -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/source-documents/extract
```

The source inventory includes `MIT_ADT_University_Fees_2026-27.xlsx`. Its course
rows are indexed with their year labels and fee values, so questions about a course,
academic year, total fee, hostel, mess or related charges can be answered from the
retrieved context. Blank year values mean that no amount was supplied, not zero;
confirm fees on the official admissions page before making payment decisions.

Scanned PDFs are reported as `ocr-required` and are not indexed as verified text until
the administrator runs OCR from the document panel (Tesseract must be installed).
Files uploaded from the admin workspace are extracted immediately into `data/extracted`;
run knowledge indexing after upload or OCR to refresh embeddings.

Remaining roadmap work includes native OCR/voice runtime installation, richer admin
management, fine-tuning preparation and expanded automated coverage. These are not
represented as working features until implemented and tested.

## Current capability blockers

- OCR endpoint: implemented, but requires a local Tesseract installation on `PATH`.
- Browser speech-to-text is available from the chat microphone button when the browser
  supports the Web Speech API and microphone access is allowed. The local voice endpoint
  is also implemented with capability reporting, but Faster-Whisper and Piper
  runtimes/models must be installed locally before server-side audio processing can be enabled.
  Authenticated audio routes are available at `/api/v1/voice/transcribe` and
  `/api/v1/voice/synthesize`; unavailable runtimes return an explicit `503`.
- WebSocket streaming: available at `/api/v1/chat/stream?token=...`; it uses local
  Ollama generation and reports token/done events.
- Admin workspace: overview metrics, knowledge re-indexing, lead status updates,
  follow-up APIs and audit activity are available after signing in as the demo admin.
- Student support workflows: profile saving, response feedback and counsellor
  escalation are available from the authenticated API and profile workspace.
- Conversation history can be loaded and deleted by its owning student. Administrators
  can select an installed local Ollama model and save generation settings.
- Administrators can upload supported documents with size/type validation, track
  document versions, extract them immediately, review escalations, update follow-up
  statuses, view analytics and export leads as CSV.
- MySQL: SQLAlchemy configuration and Alembic migration files are included; set
  `ADMISSIONS_DATABASE_URL` to a MySQL URL and run `alembic upgrade head`.
- Authentication uses bcrypt password hashes and HS256 JWT access tokens. Existing
  PBKDF2 password records and legacy local tokens remain readable for migration
  compatibility; a successful login transparently upgrades a legacy password hash.
  Newly created accounts and tokens use the stronger formats.

## Evaluation

Administrators can generate and run the local retrieval evaluation set:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/admin/evaluation/dataset -Headers $headers
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/admin/evaluation/run -Headers $headers
```

The report includes answerable retrieval hit rate and unavailable-information
precision, school-attribution accuracy and cross-school contamination rate. It is
written to `data/training/evaluation-report.json`; the unavailable case confirms
that unsupported institutional claims are not silently grounded.

## Chatbot knowledge isolation

Chat chunks now carry institution, school, information type, source document/page,
academic-year and version metadata. Query understanding resolves supported school
aliases such as SOC, SOA, SOFA and IOD, preserves the active school across follow-up
questions, and filters retrieval before Ollama sees the context. Contact-directory
rows are indexed individually so one school's contact cannot be attached to another.
When a requested school/category has no verified matching content, the assistant
returns an unavailable-information response instead of borrowing another school's
content. Re-run administrator knowledge indexing after changing extraction or OCR
data so the persisted vector index contains the latest metadata.

## Knowledge indexing

After extraction, sign in as an administrator and call:

```powershell
$login = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/auth/login `
  -ContentType application/json `
  -Body '{"email":"admin@mitadt.local","password":"admin-demo-123"}'
$headers = @{ Authorization = "Bearer $($login.token)" }
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/knowledge/index `
  -Headers $headers
```

This uses the local `all-minilm:latest` Ollama embedding model and writes the vector
index to `data/embeddings/index.json`. Chat and retrieval use that index when present.
