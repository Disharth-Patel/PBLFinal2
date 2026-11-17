from pathlib import Path

from app.db import Base


def test_remaining_workflow_tables_are_declared() -> None:
    tables = set(Base.metadata.tables)

    assert {
        "student_profiles",
        "feedback",
        "escalations",
        "model_configurations",
        "knowledge_documents",
        "document_versions",
    } <= tables
