# Architecture and development roadmap

## Target architecture

- **Frontend:** React + Vite + Tailwind, with separate student and admin route
  boundaries.
- **Backend:** FastAPI REST API with WebSocket streaming where useful.
- **Persistence:** SQLAlchemy models with SQLite for local development and MySQL
  compatibility for deployment.
- **LLM:** Ollama only, using the administrator-selected local model.
- **Retrieval:** Local document extraction, chunking, Ollama embeddings and a local
  vector index with source/page metadata.
- **Voice:** Faster-Whisper and Piper as optional local services; browser voice states
  must not be presented as telephone calls.
- **Security:** Argon2/bcrypt password hashing, JWT/session protection, role checks,
  upload validation, rate limiting and audit logging.

## Incremental delivery

1. **Source inventory and backend foundation** — completed.
2. **Extraction and ingestion** — PDF/DOCX/PPTX/XLSX/CSV/TXT processing, upload
   validation, immediate uploaded-file extraction, document metadata/version records,
   administrator-triggered OCR and OCR boundary completed; background indexing remains.
3. **RAG and Ollama** — model discovery, local Ollama embeddings, metadata-enriched
   chunks, school/category query understanding, filtered hybrid keyword/vector
   retrieval, grounded prompts, source citations and contamination evaluation
   completed; programme-level extraction remains limited by source availability.
4. **Authentication and persistence** — users, roles, profiles, conversations,
   messages, leads, follow-ups and audit logs.
5. **Student experience** — landing, registration, text chat, lead submission,
   profile editing, feedback, counsellor escalation and conversation history
   load/delete controls completed.
6. **Admin experience** — live overview, knowledge re-indexing, document management,
   lead status updates, follow-up scheduling, escalation queue, audit activity,
   model configuration, analytics and CSV export completed.
7. **Local voice** — capability reporting, authenticated transcription/synthesis
   routes and adapter boundaries completed; runtime installation and end-to-end
   audio tests remain blocked by missing local runtimes.
8. **Training/evaluation** — JSONL evaluation dataset generation, answerable retrieval
   hit rate and unavailable-information precision are implemented; model-generation
   scoring and fine-tuning preparation remain.
9. **Quality and deployment** — Alembic/MySQL configuration, Docker files, bcrypt
   password hashing, HS256 JWTs, rate limiting, audit logs, follow-up APIs and
   WebSocket streaming completed; broader security and end-to-end suites remain.

Each phase will be validated before the next phase is treated as complete. Original
institutional files stay outside generated/processed data directories.
