from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="student")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")
    leads: Mapped[list["Lead"]] = relationship(back_populates="user")
    profile: Mapped["StudentProfile | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200), default="New admission enquiry")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    phone: Mapped[str] = mapped_column(String(40), default="")
    academic_qualification: Mapped[str] = mapped_column(String(200), default="")
    interested_programme: Mapped[str] = mapped_column(String(200), default="")
    preferred_department: Mapped[str] = mapped_column(String(200), default="")
    admission_year: Mapped[str] = mapped_column(String(20), default="")
    communication_language: Mapped[str] = mapped_column(String(40), default="English")
    interests: Mapped[str] = mapped_column(Text, default="")
    user: Mapped[User] = relationship(back_populates="profile")


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    rating: Mapped[str] = mapped_column(String(20))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Escalation(Base):
    __tablename__ = "escalations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id"), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="Pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    programme: Mapped[str | None] = mapped_column(String(200), nullable=True)
    academic_qualification: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(40), default="New")
    interest_level: Mapped[str] = mapped_column(String(40), default="Medium")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user: Mapped[User] = relationship(back_populates="leads")


class FollowUp(Base):
    __tablename__ = "follow_ups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(40), default="Pending")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CourseInterest(Base):
    __tablename__ = "course_interests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    school: Mapped[str] = mapped_column(String(200), default="")
    department: Mapped[str] = mapped_column(String(200), default="")
    programme: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), default="Interested")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    activity_type: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    programme: Mapped[str | None] = mapped_column(String(200), nullable=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    resource: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ModelConfiguration(Base):
    __tablename__ = "model_configurations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(200))
    temperature: Mapped[float] = mapped_column(default=0.2)
    top_p: Mapped[float] = mapped_column(default=0.9)
    context_length: Mapped[int] = mapped_column(Integer, default=4096)
    max_tokens: Mapped[int] = mapped_column(Integer, default=512)
    active: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), unique=True)
    stored_path: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(80), default="Other")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(40), default="uploaded")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("knowledge_documents.id"))
    version: Mapped[int] = mapped_column(Integer)
    stored_path: Mapped[str] = mapped_column(String(500))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


db_url = settings.database_url.replace("sqlite:///./admissions.db", f"sqlite:///{Path(__file__).resolve().parents[1] / 'admissions.db'}")
engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)
    if db_url.startswith("sqlite"):
        with engine.begin() as connection:
            columns = {row[1] for row in connection.execute(text("PRAGMA table_info(leads)"))}
            if "phone" not in columns:
                connection.execute(text("ALTER TABLE leads ADD COLUMN phone VARCHAR(40) NOT NULL DEFAULT ''"))
