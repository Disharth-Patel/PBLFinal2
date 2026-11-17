import json
import csv
import io
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
import httpx
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import AuditLog, Conversation, DocumentVersion, Escalation, Feedback, FollowUp, KnowledgeDocument, Lead, Message, ModelConfiguration, SessionLocal, StudentProfile, User, init_db
from app.schemas import (
    AuthResponse,
    ChatRequest,
    ChatResponse,
    ExtractionResult,
    EscalationRequest,
    FeedbackRequest,
    FollowUpRequest,
    HealthResponse,
    ReadinessResponse,
    IndexResult,
    LeadRequest,
    LeadUpdateRequest,
    LoginRequest,
    ConversationUpdateRequest,
    ModelConfigurationRequest,
    StatusUpdateRequest,
    DocumentUpdateRequest,
    OllamaStatus,
    ProfileRequest,
    RegisterRequest,
    SourceDocument,
    RetrievalRequest,
    RetrievalResult,
)
from app.services.auth import create_token, decode_token, hash_password, needs_password_upgrade, verify_password
from app.services.controls import audit, rate_limiter
from app.services.extraction import extract_document, extract_source_documents
from app.services.inventory import build_source_inventory
from app.services.ollama import OllamaConnectionError, discover_local_models, local_model_names
from app.services.rag import (
    embed_texts,
    generate_answer,
    grounded_prompt,
    load_chunks,
    load_index,
    retrieve,
    save_index,
    structured_contact_answer,
    understand_query,
    vector_retrieve,
)
from app.services.voice import capabilities as voice_capabilities, synthesize, transcribe
from app.services.ocr import capability as ocr_capability, ocr_pdf
from app.services.evaluation import build_dataset, evaluate_retrieval

app = FastAPI(title=settings.app_name, version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        'camera=(), microphone=(self "http://localhost:5173" "http://127.0.0.1:5173")',
    )
    return response


@app.middleware("http")
async def request_rate_limit(request: Request, call_next):
    client = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(client, settings.rate_limit_requests, settings.rate_limit_window_seconds):
        return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
    return await call_next(request)


@app.on_event("startup")
def startup() -> None:
    init_db()

@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "health": "/health", "api": "/api/v1"}


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(authorization: str | None = Header(default=None), db: Session = Depends(db_session)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentication required")
    try:
        payload = decode_token(authorization[7:])
        user = db.get(User, int(payload["sub"]))
    except (ValueError, KeyError, TypeError):
        user = None
    if not user:
        raise HTTPException(401, "Invalid authentication token")
    return user


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", ollama_url=settings.ollama_base_url, source_directory=settings.source_directory)

@app.get("/ready", response_model=ReadinessResponse)
def readiness(db: Session = Depends(db_session)) -> ReadinessResponse:
    try:
        db.execute(text("SELECT 1"))
    except Exception as error:
        raise HTTPException(503, "Database is not ready") from error
    return ReadinessResponse(status="ready", database="ok")


@app.get("/api/v1/voice/capabilities")
def voice_status() -> dict:
    return voice_capabilities()


@app.post("/api/v1/voice/transcribe")
async def transcribe_voice(audio: UploadFile = File(...), user: User = Depends(current_user)) -> dict:
    content = await audio.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, "Audio exceeds the upload size limit")
    try:
        text = transcribe(content, audio.filename or "audio.wav", settings.whisper_model)
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error
    return {"text": text, "provider": "Faster-Whisper"}


@app.post("/api/v1/voice/synthesize")
def synthesize_voice(request: dict[str, str], user: User = Depends(current_user)) -> Response:
    text = request.get("text", "").strip()
    if not text:
        raise HTTPException(422, "Text cannot be empty")
    try:
        audio = synthesize(text, settings.piper_executable, settings.piper_voice)
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error
    return Response(content=audio, media_type="audio/wav")


@app.get("/api/v1/ocr/capabilities")
def ocr_status() -> dict:
    return ocr_capability()


@app.post("/api/v1/admin/evaluation/dataset")
def create_evaluation_dataset(user: User = Depends(current_user)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    return build_dataset(settings.extracted_directory, settings.source_directory / "data" / "training" / "evaluation.jsonl")


@app.post("/api/v1/admin/evaluation/run")
def run_evaluation(user: User = Depends(current_user)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    report = evaluate_retrieval(settings.source_directory / "data" / "training" / "evaluation.jsonl", settings.extracted_directory)
    report_path = settings.source_directory / "data" / "training" / "evaluation-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {**report, "report_path": str(report_path)}


@app.post("/api/v1/ocr/{filename}")
def run_ocr(filename: str, user: User = Depends(current_user)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    source = settings.source_directory / filename
    if source.suffix.lower() != ".pdf" or not source.is_file():
        raise HTTPException(404, "PDF source document not found")
    try:
        pages = ocr_pdf(source, settings.extracted_directory)
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error
    return {"filename": filename, "pages": pages, "status": "ocr-extracted"}


@app.get("/api/v1/source-documents", response_model=list[SourceDocument])
def source_documents() -> list[SourceDocument]:
    return build_source_inventory(settings.source_directory)


@app.post("/api/v1/source-documents/extract", response_model=list[ExtractionResult])
def extract_documents() -> list[ExtractionResult]:
    return extract_source_documents(settings.source_directory, settings.extracted_directory)


@app.post("/api/v1/admin/documents")
async def upload_document(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    allowed = {".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".txt", ".json"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(415, "Unsupported document type")
    settings.upload_directory.mkdir(parents=True, exist_ok=True)
    target = settings.upload_directory / Path(file.filename or "upload").name
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, "File exceeds the upload size limit")
    target.write_bytes(content)
    try:
        extraction = extract_document(target, settings.extracted_directory)
    except (OSError, ValueError) as error:
        target.unlink(missing_ok=True)
        raise HTTPException(422, f"Document extraction failed: {error}") from error
    document = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.filename == target.name))
    version = document.version + 1 if document else 1
    if document:
        document.version = version
        document.stored_path = str(target)
        document.size_bytes = len(content)
        document.status = extraction.status
    else:
        document = KnowledgeDocument(filename=target.name, stored_path=str(target), version=version, size_bytes=len(content), uploaded_by=user.id, status=extraction.status)
        db.add(document)
        db.flush()
    db.add(DocumentVersion(document_id=document.id, version=version, stored_path=str(target), size_bytes=len(content)))
    audit(db, user.id, "upload", f"document:{target.name}", f"version={version}")
    db.commit()
    return {
        "id": document.id,
        "filename": document.filename,
        "version": version,
        "status": document.status,
        "extraction": {
            "records": extraction.records,
            "characters": extraction.extracted_characters,
            "output_path": extraction.output_path,
        },
    }


@app.get("/api/v1/admin/documents")
def list_documents(user: User = Depends(current_user), db: Session = Depends(db_session)) -> list[dict]:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    rows = db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())).all()
    return [{"id": row.id, "filename": row.filename, "category": row.category, "version": row.version, "status": row.status, "size_bytes": row.size_bytes} for row in rows]


@app.post("/api/v1/admin/documents/{document_id}/ocr")
def ocr_document(document_id: int, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    document = db.get(KnowledgeDocument, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    source = Path(document.stored_path)
    if source.suffix.lower() != ".pdf" or not source.is_file():
        raise HTTPException(422, "Only stored PDF documents can be OCR processed")
    try:
        pages = ocr_pdf(source, settings.extracted_directory)
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error
    document.status = "text-extracted" if pages else "ocr-empty"
    audit(db, user.id, "ocr", f"document:{document.filename}", f"pages={pages}")
    db.commit()
    return {"id": document.id, "filename": document.filename, "pages": pages, "status": document.status}


@app.patch("/api/v1/admin/documents/{document_id}")
def update_document(document_id: int, request: DocumentUpdateRequest, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    document = db.get(KnowledgeDocument, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    document.category = request.category.strip() or "Other"
    audit(db, user.id, "update", f"document:{document.filename}")
    db.commit()
    return {"id": document.id, "category": document.category}


@app.delete("/api/v1/admin/documents/{document_id}")
def delete_document(document_id: int, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    document = db.get(KnowledgeDocument, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    path = Path(document.stored_path)
    if path.exists() and path.is_relative_to(settings.upload_directory):
        path.unlink()
    db.query(DocumentVersion).filter(DocumentVersion.document_id == document.id).delete()
    db.delete(document)
    audit(db, user.id, "delete", f"document:{document.filename}")
    db.commit()
    return {"status": "deleted"}


@app.post("/api/v1/knowledge/index", response_model=IndexResult)
async def index_knowledge(user: User = Depends(current_user)) -> IndexResult:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    chunks = load_chunks(settings.extracted_directory, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise HTTPException(409, "No extracted text is available to index")
    try:
        embeddings = await embed_texts(settings.ollama_base_url, settings.embedding_model, [chunk["text"] for chunk in chunks])
    except Exception as error:
        raise HTTPException(502, f"Local embedding request failed: {error}") from error
    if len(embeddings) != len(chunks):
        raise HTTPException(502, "Embedding service returned an incomplete result")
    save_index(settings.vector_index_path, chunks, embeddings)
    return IndexResult(chunks=len(chunks), embedded=len(embeddings), output_path=str(settings.vector_index_path), status="indexed")


@app.post("/api/v1/knowledge/retrieve", response_model=list[RetrievalResult])
async def retrieve_knowledge(request: RetrievalRequest, user: User = Depends(current_user)) -> list[RetrievalResult]:
    if not request.query.strip():
        raise HTTPException(422, "Query cannot be empty")
    index = load_index(settings.vector_index_path)
    scope = understand_query(request.query)
    if index["embeddings"]:
        try:
            query_embedding = (await embed_texts(settings.ollama_base_url, settings.embedding_model, [request.query]))[0]
            matches = vector_retrieve(query_embedding, index, request.limit, scope)
        except Exception as error:
            raise HTTPException(502, f"Local retrieval request failed: {error}") from error
    else:
        matches = retrieve(request.query, load_chunks(settings.extracted_directory, settings.chunk_size, settings.chunk_overlap), request.limit, scope)
    return [RetrievalResult(**match) for match in matches]


@app.get("/api/v1/ollama/status", response_model=OllamaStatus)
def ollama_status() -> OllamaStatus:
    try:
        models = discover_local_models(settings.ollama_base_url)
    except OllamaConnectionError as error:
        return OllamaStatus(connected=False, url=settings.ollama_base_url, error=str(error))
    return OllamaStatus(connected=True, url=settings.ollama_base_url, models=models)


@app.post("/api/v1/auth/register", response_model=AuthResponse)
def register(request: RegisterRequest, db: Session = Depends(db_session)) -> AuthResponse:
    email = request.email.strip().lower()
    if len(request.password) < 8:
        raise HTTPException(422, "Password must contain at least 8 characters")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(name=request.name.strip(), email=email, password_hash=hash_password(request.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthResponse(token=create_token(user.id, user.role), user={"id": user.id, "name": user.name, "email": user.email, "role": user.role})


@app.post("/api/v1/auth/login", response_model=AuthResponse)
def login(request: LoginRequest, db: Session = Depends(db_session)) -> AuthResponse:
    client_key = f"login:{request.email.strip().lower()}"
    if not rate_limiter.allow(client_key, min(settings.rate_limit_requests, 10), settings.rate_limit_window_seconds):
        raise HTTPException(429, "Too many login attempts")
    user = db.scalar(select(User).where(User.email == request.email.strip().lower()))
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect")
    if needs_password_upgrade(user.password_hash):
        user.password_hash = hash_password(request.password)
    audit(db, user.id, "login", "user")
    db.commit()
    return AuthResponse(token=create_token(user.id, user.role), user={"id": user.id, "name": user.name, "email": user.email, "role": user.role})


@app.get("/api/v1/auth/me")
def me(user: User = Depends(current_user)) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


@app.get("/api/v1/profile")
def get_profile(user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    return {"name": user.name, "email": user.email, **({field: getattr(profile, field) for field in ("phone", "academic_qualification", "interested_programme", "preferred_department", "admission_year", "communication_language", "interests")} if profile else {})}


@app.put("/api/v1/profile")
def update_profile(request: ProfileRequest, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    if not profile:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
    for field in request.model_fields:
        setattr(profile, field, getattr(request, field).strip())
    audit(db, user.id, "update", "student_profile")
    db.commit()
    return {"status": "saved"}


@app.post("/api/v1/feedback")
def submit_feedback(request: FeedbackRequest, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    if request.rating not in {"positive", "negative"}:
        raise HTTPException(422, "rating must be positive or negative")
    if request.message_id and not db.scalar(select(Message).join(Conversation).where(Message.id == request.message_id, Conversation.user_id == user.id)):
        raise HTTPException(404, "Message not found")
    db.add(Feedback(user_id=user.id, message_id=request.message_id, rating=request.rating, comment=request.comment.strip()))
    audit(db, user.id, "create", "feedback")
    db.commit()
    return {"status": "recorded"}


@app.post("/api/v1/escalations")
def request_escalation(request: EscalationRequest, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    if request.conversation_id and not db.scalar(select(Conversation).where(Conversation.id == request.conversation_id, Conversation.user_id == user.id)):
        raise HTTPException(404, "Conversation not found")
    escalation = Escalation(user_id=user.id, conversation_id=request.conversation_id, reason=request.reason.strip())
    db.add(escalation)
    audit(db, user.id, "create", "escalation")
    db.commit()
    db.refresh(escalation)
    return {"id": escalation.id, "status": escalation.status}


@app.get("/api/v1/conversations")
def conversations(user: User = Depends(current_user), db: Session = Depends(db_session)) -> list[dict]:
    rows = db.scalars(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.created_at.desc())).all()
    return [{"id": row.id, "title": row.title, "created_at": row.created_at.isoformat()} for row in rows]


@app.patch("/api/v1/conversations/{conversation_id}")
def rename_conversation(conversation_id: int, request: ConversationUpdateRequest, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    conversation = db.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id))
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    title = request.title.strip()
    if not title:
        raise HTTPException(422, "Title cannot be empty")
    conversation.title = title[:200]
    audit(db, user.id, "update", f"conversation:{conversation_id}")
    db.commit()
    return {"id": conversation.id, "title": conversation.title}


@app.delete("/api/v1/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    conversation = db.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id))
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    db.delete(conversation)
    audit(db, user.id, "delete", f"conversation:{conversation_id}")
    db.commit()
    return {"status": "deleted"}


@app.get("/api/v1/conversations/{conversation_id}/messages")
def messages(conversation_id: int, user: User = Depends(current_user), db: Session = Depends(db_session)) -> list[dict]:
    conversation = db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(404, "Conversation not found")
    return [{"role": row.role, "content": row.content, "sources": json.loads(row.sources)} for row in conversation.messages]


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user: User = Depends(current_user), db: Session = Depends(db_session)) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(422, "Message cannot be empty")
    conversation = db.get(Conversation, request.conversation_id) if request.conversation_id else None
    if conversation and conversation.user_id != user.id:
        raise HTTPException(404, "Conversation not found")
    if not conversation:
        conversation = Conversation(user_id=user.id, title=request.message[:80])
        db.add(conversation)
        db.flush()
    previous = [{"role": message.role, "content": message.content} for message in conversation.messages]
    scope = understand_query(request.message, previous)
    index = load_index(settings.vector_index_path)
    if index["embeddings"]:
        try:
            query_embedding = (await embed_texts(settings.ollama_base_url, settings.embedding_model, [request.message]))[0]
            sources = vector_retrieve(query_embedding, index, 5, scope)
        except Exception as error:
            raise HTTPException(502, f"Local retrieval request failed: {error}") from error
        lexical_sources = retrieve(
            request.message,
            load_chunks(settings.extracted_directory, settings.chunk_size, settings.chunk_overlap),
            limit=3,
            scope=scope,
        )
        seen = {(item["source"], item["location"]) for item in sources}
        sources.extend(item for item in lexical_sources if (item["source"], item["location"]) not in seen)
        sources = sources[:8]
    else:
        sources = retrieve(request.message, load_chunks(settings.extracted_directory, settings.chunk_size, settings.chunk_overlap), scope=scope)
    active_model = request.model
    if not active_model:
        configured = db.scalar(select(ModelConfiguration).where(ModelConfiguration.active.is_(True)))
        active_model = configured.model_name if configured else "qwen2.5:1.5b-instruct"
    configured = db.scalar(select(ModelConfiguration).where(ModelConfiguration.active.is_(True)))
    try:
        if active_model not in local_model_names(settings.ollama_base_url):
            raise HTTPException(422, "Selected model is not installed locally in Ollama")
    except OllamaConnectionError as error:
        raise HTTPException(503, str(error)) from error
    try:
        answer = await generate_answer(
            settings.ollama_base_url,
            active_model,
            request.message,
            sources,
            previous,
            scope,
            temperature=configured.temperature if configured else 0.0,
            top_p=configured.top_p if configured else 1.0,
            context_length=configured.context_length if configured else 4096,
            max_tokens=configured.max_tokens if configured else 512,
        )
    except Exception as error:
        raise HTTPException(502, f"Local Ollama request failed: {error}") from error
    if scope.get("information_type") == "contact_information":
        answer = structured_contact_answer(sources) or answer
    db.add(Message(conversation_id=conversation.id, role="user", content=request.message))
    db.add(Message(conversation_id=conversation.id, role="assistant", content=answer, sources=json.dumps(sources)))
    db.commit()
    response_sources = [
        {
            "source": str(item["source"]),
            "location": str(item["location"]),
            "text": str(item["text"]),
            "score": float(item["score"]),
        }
        for item in sources
    ]
    return ChatResponse(conversation_id=conversation.id, answer=answer, sources=response_sources)


@app.post("/api/v1/leads")
def create_lead(request: LeadRequest, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    lead = Lead(user_id=user.id, programme=request.programme, academic_qualification=request.academic_qualification, notes=request.notes)
    db.add(lead)
    audit(db, user.id, "create", "lead")
    db.commit()
    db.refresh(lead)
    return {"id": lead.id, "status": lead.status, "interest_level": lead.interest_level}


@app.get("/api/v1/admin/overview")
def admin_overview(user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    return {
        "students": db.scalar(select(func.count(User.id)).where(User.role == "student")) or 0,
        "conversations": db.scalar(select(func.count(Conversation.id))) or 0,
        "leads": db.scalar(select(func.count(Lead.id))) or 0,
        "indexed_documents": len(list(settings.extracted_directory.glob("*.json"))),
    }


@app.get("/api/v1/admin/model-configuration")
def get_model_configuration(user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    config = db.scalar(select(ModelConfiguration).where(ModelConfiguration.active.is_(True)))
    if not config:
        return {"model_name": "qwen2.5:1.5b-instruct", "temperature": 0.0, "top_p": 1.0, "context_length": 4096, "max_tokens": 512, "active": False}
    return {field: getattr(config, field) for field in ("model_name", "temperature", "top_p", "context_length", "max_tokens", "active")}


@app.put("/api/v1/admin/model-configuration")
def update_model_configuration(request: ModelConfigurationRequest, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    if not 0 <= request.temperature <= 2 or not 0 <= request.top_p <= 1:
        raise HTTPException(422, "temperature or top_p is outside the supported range")
    if request.context_length < 256 or request.max_tokens < 1:
        raise HTTPException(422, "context_length and max_tokens must be positive")
    try:
        if request.model_name not in local_model_names(settings.ollama_base_url):
            raise HTTPException(422, "Model must be installed locally in Ollama")
    except OllamaConnectionError as error:
        raise HTTPException(503, str(error)) from error
    db.query(ModelConfiguration).update({"active": False})
    config = ModelConfiguration(**request.model_dump(), active=True)
    db.add(config)
    audit(db, user.id, "update", "model_configuration", request.model_name)
    db.commit()
    return {"status": "saved", **request.model_dump(), "active": True}


@app.get("/api/v1/admin/leads")
def admin_leads(user: User = Depends(current_user), db: Session = Depends(db_session)) -> list[dict]:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    leads = db.scalars(select(Lead).order_by(Lead.created_at.desc())).all()
    return [{"id": lead.id, "user_id": lead.user_id, "programme": lead.programme, "status": lead.status, "interest_level": lead.interest_level, "notes": lead.notes, "created_at": lead.created_at.isoformat()} for lead in leads]


@app.patch("/api/v1/admin/leads/{lead_id}")
def update_lead(lead_id: int, request: LeadUpdateRequest, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    for field in ("status", "interest_level", "notes"):
        value = getattr(request, field)
        if value is not None:
            setattr(lead, field, value)
    audit(db, user.id, "update", f"lead:{lead_id}")
    db.commit()
    return {"id": lead.id, "status": lead.status, "interest_level": lead.interest_level}


@app.post("/api/v1/admin/follow-ups")
def create_follow_up(request: FollowUpRequest, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    lead = db.get(Lead, request.lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    try:
        due_at = datetime.fromisoformat(request.due_at)
    except ValueError as error:
        raise HTTPException(422, "due_at must be an ISO datetime") from error
    follow_up = FollowUp(lead_id=lead.id, due_at=due_at, notes=request.notes)
    db.add(follow_up)
    audit(db, user.id, "create", f"follow_up:{lead.id}")
    db.commit()
    db.refresh(follow_up)
    return {"id": follow_up.id, "lead_id": follow_up.lead_id, "due_at": follow_up.due_at.isoformat(), "status": follow_up.status}


@app.get("/api/v1/admin/follow-ups")
def list_follow_ups(user: User = Depends(current_user), db: Session = Depends(db_session)) -> list[dict]:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    rows = db.scalars(select(FollowUp).order_by(FollowUp.due_at)).all()
    return [{"id": row.id, "lead_id": row.lead_id, "due_at": row.due_at.isoformat(), "status": row.status, "notes": row.notes} for row in rows]


@app.patch("/api/v1/admin/follow-ups/{follow_up_id}")
def update_follow_up(follow_up_id: int, request: StatusUpdateRequest, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    follow_up = db.get(FollowUp, follow_up_id)
    if not follow_up:
        raise HTTPException(404, "Follow-up not found")
    if request.status not in {"Pending", "In Progress", "Completed", "Cancelled"}:
        raise HTTPException(422, "Unsupported follow-up status")
    follow_up.status = request.status
    audit(db, user.id, "update", f"follow_up:{follow_up_id}", request.status)
    db.commit()
    return {"id": follow_up.id, "status": follow_up.status}


@app.get("/api/v1/admin/escalations")
def list_escalations(user: User = Depends(current_user), db: Session = Depends(db_session)) -> list[dict]:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    rows = db.scalars(select(Escalation).order_by(Escalation.created_at.desc())).all()
    return [{"id": row.id, "user_id": row.user_id, "conversation_id": row.conversation_id, "reason": row.reason, "status": row.status, "created_at": row.created_at.isoformat()} for row in rows]


@app.patch("/api/v1/admin/escalations/{escalation_id}")
def update_escalation(escalation_id: int, request: StatusUpdateRequest, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    escalation = db.get(Escalation, escalation_id)
    if not escalation:
        raise HTTPException(404, "Escalation not found")
    if request.status not in {"Pending", "In Progress", "Resolved", "Cancelled"}:
        raise HTTPException(422, "Unsupported escalation status")
    escalation.status = request.status
    audit(db, user.id, "update", f"escalation:{escalation_id}", request.status)
    db.commit()
    return {"id": escalation.id, "status": escalation.status}


@app.get("/api/v1/admin/analytics")
def analytics(user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    status_counts = db.execute(select(Lead.status, func.count(Lead.id)).group_by(Lead.status)).all()
    programme_counts = db.execute(select(Lead.programme, func.count(Lead.id)).group_by(Lead.programme)).all()
    feedback_counts = db.execute(select(Feedback.rating, func.count(Feedback.id)).group_by(Feedback.rating)).all()
    return {
        "lead_status": {status or "Unspecified": count for status, count in status_counts},
        "programme": {programme or "Unspecified": count for programme, count in programme_counts},
        "feedback": {rating: count for rating, count in feedback_counts},
        "escalations_pending": db.scalar(select(func.count(Escalation.id)).where(Escalation.status == "Pending")) or 0,
    }


@app.get("/api/v1/admin/leads/export")
def export_leads(user: User = Depends(current_user), db: Session = Depends(db_session)) -> StreamingResponse:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "user_id", "programme", "academic_qualification", "status", "interest_level", "notes", "created_at"])
    for lead in db.scalars(select(Lead).order_by(Lead.created_at.desc())):
        writer.writerow([lead.id, lead.user_id, lead.programme, lead.academic_qualification, lead.status, lead.interest_level, lead.notes, lead.created_at.isoformat()])
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=admission-leads.csv"})


@app.get("/api/v1/admin/audit-logs")
def audit_logs(user: User = Depends(current_user), db: Session = Depends(db_session)) -> list[dict]:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)).all()
    return [{"id": row.id, "user_id": row.user_id, "action": row.action, "resource": row.resource, "detail": row.detail, "created_at": row.created_at.isoformat()} for row in rows]


@app.websocket("/api/v1/chat/stream")
async def chat_stream(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    requested_model = websocket.query_params.get("model")
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return
    try:
        payload = decode_token(token)
        with SessionLocal() as db:
            if not db.get(User, int(payload["sub"])):
                raise ValueError("User not found")
            configured = db.scalar(select(ModelConfiguration).where(ModelConfiguration.active.is_(True)))
            model = requested_model or (configured.model_name if configured else "qwen2.5:1.5b-instruct")
            generation_options = {
                "temperature": configured.temperature if configured else 0.0,
                "top_p": configured.top_p if configured else 1.0,
                "num_ctx": configured.context_length if configured else 4096,
                "num_predict": configured.max_tokens if configured else 512,
            }
    except (ValueError, KeyError, TypeError):
        await websocket.close(code=1008, reason="Invalid authentication token")
        return
    try:
        if model not in local_model_names(settings.ollama_base_url):
            await websocket.close(code=1008, reason="Selected model is not installed locally")
            return
    except OllamaConnectionError:
        await websocket.close(code=1011, reason="Ollama is unavailable")
        return
    await websocket.accept()
    try:
        while True:
            question = (await websocket.receive_json()).get("message", "").strip()
            if not question:
                await websocket.send_json({"type": "error", "detail": "Message cannot be empty"})
                continue
            scope = understand_query(question)
            index = load_index(settings.vector_index_path)
            if index["embeddings"]:
                query_embedding = (await embed_texts(settings.ollama_base_url, settings.embedding_model, [question]))[0]
                sources = vector_retrieve(query_embedding, index, 5, scope)
            else:
                sources = retrieve(question, load_chunks(settings.extracted_directory, settings.chunk_size, settings.chunk_overlap), scope=scope)
            await websocket.send_json({"type": "sources", "sources": sources})
            prompt = grounded_prompt(question, sources, [], scope)
            async with httpx.AsyncClient(timeout=90) as client:
                async with client.stream(
                    "POST",
                    f"{settings.ollama_base_url.rstrip('/')}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": True, "options": generation_options},
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        payload = json.loads(line)
                        if payload.get("response"):
                            await websocket.send_json({"type": "token", "content": payload["response"]})
                        if payload.get("done"):
                            await websocket.send_json({"type": "done"})
    except (WebSocketDisconnect, httpx.HTTPError):
        return
