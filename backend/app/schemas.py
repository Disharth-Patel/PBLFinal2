from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class SourceDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    filename: str
    format: str
    size_bytes: int
    pages_or_sheets: int | None = None
    extracted_characters: int
    extraction_status: str
    path: str


class HealthResponse(BaseModel):
    status: str
    ollama_url: str
    source_directory: Path


class ReadinessResponse(BaseModel):
    status: str
    database: str


class OllamaModel(BaseModel):
    name: str
    size_bytes: int
    parameter_size: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    is_local: bool = True


class OllamaStatus(BaseModel):
    connected: bool
    url: str
    models: list[OllamaModel] = Field(default_factory=list)
    error: str | None = None


class ExtractionResult(BaseModel):
    filename: str
    output_path: str
    records: int
    extracted_characters: int
    status: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    message: str
    model: str | None = None


class RetrievalResult(BaseModel):
    source: str
    location: str
    text: str
    score: float


class ChatResponse(BaseModel):
    conversation_id: int
    answer: str
    sources: list[dict[str, str | float]]


class LeadRequest(BaseModel):
    programme: str | None = None
    academic_qualification: str | None = None
    notes: str = ""


class IndexResult(BaseModel):
    chunks: int
    embedded: int
    output_path: str
    status: str


class RetrievalRequest(BaseModel):
    query: str
    limit: int = 5


class FollowUpRequest(BaseModel):
    lead_id: int
    due_at: str
    notes: str = ""


class LeadUpdateRequest(BaseModel):
    status: str | None = None
    interest_level: str | None = None
    notes: str | None = None


class ProfileRequest(BaseModel):
    phone: str = ""
    academic_qualification: str = ""
    interested_programme: str = ""
    preferred_department: str = ""
    admission_year: str = ""
    communication_language: str = "English"
    interests: str = ""


class FeedbackRequest(BaseModel):
    message_id: int | None = None
    rating: str
    comment: str = ""


class EscalationRequest(BaseModel):
    conversation_id: int | None = None
    reason: str


class ConversationUpdateRequest(BaseModel):
    title: str


class ModelConfigurationRequest(BaseModel):
    model_name: str
    temperature: float = 0.0
    top_p: float = 0.9
    context_length: int = 4096
    max_tokens: int = 512


class DocumentUpdateRequest(BaseModel):
    category: str = "Other"


class StatusUpdateRequest(BaseModel):
    status: str
