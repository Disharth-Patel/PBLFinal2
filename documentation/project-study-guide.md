# Project Study Guide

## 1. Project purpose

This is a local-first AI admissions assistant for MIT ADT University. It combines a
React user interface, a FastAPI backend, SQLite or MySQL persistence, local Ollama
generation and a document retrieval index. It is designed to ground admissions
answers in uploaded institutional documents rather than allowing the model to invent
facts.

## 2. Main workflow

1. An administrator uploads PDF, Word, PowerPoint, Excel, CSV, TXT or JSON content.
2. The backend extracts text or tabular records into JSON files under `data/extracted`.
3. The administrator clicks **Re-index knowledge**.
4. Ollama embedding requests are generated for each text chunk.
5. The chunks and vectors are stored in `data/embeddings/index.json`.
6. A student asks a question through the React chat.
7. The backend resolves the query school/category, embeds or lexically searches the
   query, filters matching chunks and checks whether verified context exists.
8. Unsupported questions return a fixed unavailable-information response and no
   source citations. Supported questions are answered from retrieved context.
9. The conversation, retrieved sources and user activity are persisted.
10. Students can submit enquiries; their mobile number is required and available to
    administrators for follow-up.

## 3. Repository structure

- `frontend/src/main.jsx`: React screens, authentication, chat, profile, leads and
  administrator workspace.
- `frontend/src/styles.css`, `frontend/src/admin.css`: application styling.
- `backend/app/main.py`: FastAPI routes, authentication enforcement and workflows.
- `backend/app/db.py`: SQLAlchemy models and database initialization.
- `backend/app/schemas.py`: Pydantic request/response validation.
- `backend/app/config.py`: environment settings and runtime safety validation.
- `backend/app/services/auth.py`: password hashing and JWT implementation.
- `backend/app/services/rag.py`: extraction metadata, retrieval, embeddings and prompts.
- `backend/app/services/ocr.py`: local Tesseract OCR integration.
- `backend/app/services/voice.py`: Faster-Whisper/Piper capability integration.
- `backend/app/services/evaluation.py`: retrieval evaluation report generation.
- `backend/tests/`: backend unit and contract tests.
- `migrations/versions/`: Alembic database migrations.
- `data/extracted/`: extracted structured JSON source records.
- `data/uploads/`: administrator-uploaded documents.
- `data/embeddings/index.json`: persisted vector knowledge index.
- `documentation/`: project inventory and roadmap documentation.

## 4. Important backend functions

- `init_db`: creates declared tables and applies the SQLite lead-phone compatibility
  column when needed.
- `current_user`: validates bearer JWT tokens and loads the user.
- `upload_document`: validates file type and size, stores the file and extracts it.
- `index_knowledge`: loads extracted records, creates embeddings and rebuilds the index.
- `retrieve_knowledge`: performs vector or lexical retrieval for an administrator query.
- `chat`: owns conversation persistence, query scope resolution, retrieval and generation.
- `create_lead`: validates mobile number, creates the lead and notifies administrators.
- `update_profile`: persists student contact and admission preference details.
- `admin_leads` / `export_leads`: expose and export lead data, including phone number.
- `generate_answer`: sends a grounded prompt to local Ollama.
- `has_verified_context`: prevents calls to the model and prevents source display when
  retrieval does not produce sufficiently relevant verified context.

## 5. Authentication and authorization

Passwords use bcrypt with an upgrade path for existing legacy password hashes. JWT
access tokens carry the user ID and role. Protected routes call `current_user`; admin
routes additionally verify `user.role == "admin"`. Conversation and notification
routes restrict rows to the owning user. CORS is explicit and wildcard origins are
rejected. Rate limiting protects login and shared API traffic.

## 6. Data model

Core tables include users, conversations, messages, student profiles, leads,
course interests, feedback, escalations, follow-ups, notifications, audit logs,
model configuration, knowledge documents and document versions. Lead records retain
the submitted phone number in addition to the profile phone.

## 7. RAG and AI behavior

`rag.py` classifies source metadata by school and information category. Retrieval
matches the active school and category when the question specifies them. It first
uses vector similarity and can supplement it with lexical retrieval. The grounded
prompt forbids facts outside the supplied context and requests a fixed unavailable
response when the context is insufficient. Unsupported questions return no sources.

## 8. Performance choices

- Default generation context is 2048 tokens.
- Default generation limit is 256 tokens.
- Temperature defaults to 0.0 for stable admissions answers.
- Retrieval combines only a small set of relevant vector and lexical matches.
- Unsupported questions skip Ollama generation entirely.
- The existing WebSocket route remains available for streaming providers if the UI
  is later switched to token streaming.

## 9. Audit findings and fixes

Fixed in this pass:

- Re-indexing is wired to a real backend endpoint and reports progress/errors.
- Uploaded documents already extracted locally are visible to the re-index endpoint.
- Source extraction is protected by administrator authentication.
- Unsupported-chat responses no longer return source page metadata.
- Lead submission requires and persists a mobile number.
- Admin lead table, detail view and CSV export expose the stored phone number.
- Registration now flushes the new user before recording its activity.
- Default generation sizes were reduced for lower local latency.
- Frontend build and 25 backend tests pass.

Remaining operational requirements:

- Run `alembic upgrade head` in deployed databases as the standard migration path.
  The application also has SQLite compatibility initialization for `phone`.
- Configure a strong `ADMISSIONS_JWT_SECRET` in production.
- Configure production CORS with HTTPS origins.
- Install Tesseract for OCR and Faster-Whisper/Piper only where server-side voice is
  required.
- Keep `ollama`, the embedding model and the selected generation model running locally.
- Replace demo credentials before any public deployment.
