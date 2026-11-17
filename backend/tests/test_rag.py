from pathlib import Path

from app.schemas import ChatResponse
from app.services.rag import load_chunks, retrieve, structured_contact_answer, understand_query, vector_retrieve


def test_chunks_preserve_source_locations() -> None:
    chunks = load_chunks(Path(__file__).resolve().parents[2] / "data" / "extracted", chunk_size=300, overlap=40)

    assert chunks
    assert {chunk["source"] for chunk in chunks} >= {
        "SAP_Brochure 2026.pdf",
        "institution_contact_directory.xlsx",
    }
    assert all(chunk["location"] for chunk in chunks)


def test_vector_retrieval_orders_by_cosine_similarity() -> None:
    index = {
        "chunks": [
            {"source": "a.txt", "location": "document", "text": "admissions"},
            {"source": "b.txt", "location": "document", "text": "campus"},
        ],
        "embeddings": [[1.0, 0.0], [0.0, 1.0]],
    }

    matches = vector_retrieve([0.9, 0.1], index, limit=1)

    assert matches[0]["source"] == "a.txt"
    assert matches[0]["score"] > 0.9


def test_chat_response_accepts_numeric_retrieval_scores() -> None:
    response = ChatResponse(
        conversation_id=1,
        answer="Verified answer",
        sources=[{"source": "brochure.pdf", "location": "page 1", "text": "content", "score": 0.42}],
    )

    assert response.sources[0]["score"] == 0.42


def test_query_scope_filters_school_metadata() -> None:
    chunks = [
        {"source": "soc.pdf", "location": "page 1", "text": "admission process", "school_name": "School of Computing (SOC)", "information_type": "admission_process"},
        {"source": "soa.pdf", "location": "page 1", "text": "admission process", "school_name": "School of Architecture (SOA)", "information_type": "admission_process"},
    ]

    scope = understand_query("What is the SOC admission process?")
    matches = retrieve("admission process", chunks, scope=scope)

    assert scope["school_name"] == "School of Computing (SOC)"
    assert [match["source"] for match in matches] == ["soc.pdf"]


def test_school_admission_query_does_not_use_contact_or_general_chunks() -> None:
    chunks = load_chunks(Path(__file__).resolve().parents[2] / "data" / "extracted")
    scope = understand_query("What is the SOC admission process?")
    matches = retrieve("SOC admission process", chunks, scope=scope)

    assert all(match["school_name"] == "School of Computing (SOC)" for match in matches)
    assert all(match["information_type"] == "admission_process" for match in matches)


def test_fee_workbook_chunks_preserve_headers_and_fee_scope() -> None:
    chunks = load_chunks(Path(__file__).resolve().parents[2] / "data" / "extracted")
    aerospace = next(
        chunk
        for chunk in chunks
        if chunk["source"] == "MIT_ADT_University_Fees_2026-27.xlsx"
        and "Aerospace Engineering" in chunk["text"]
    )

    assert aerospace["information_type"] == "fees"
    assert "2026-27 (₹): 247000" in aerospace["text"]
    assert "Total (₹): 1060000" in aerospace["text"]
    read_me = next(
        chunk
        for chunk in chunks
        if chunk["source"] == "MIT_ADT_University_Fees_2026-27.xlsx"
        and "compiled from the preceding" in chunk["text"]
    )
    assert read_me["information_type"] == "general"

    scope = understand_query("What is the Aerospace Engineering fee for 2026-27?")
    matches = retrieve("Aerospace Engineering 2026-27 fee", chunks, scope=scope)
    assert matches
    assert matches[0]["source"] == "MIT_ADT_University_Fees_2026-27.xlsx"
    assert matches[0]["location"] == "sheet All Courses row 2"


def test_fee_json_courses_are_retrievable() -> None:
    chunks = load_chunks(Path(__file__).resolve().parents[2] / "data" / "extracted")
    matches = retrieve(
        "What is the Aerospace Engineering fee for 2026-27?",
        chunks,
        scope=understand_query("What is the Aerospace Engineering fee for 2026-27?"),
    )
    assert any("Aerospace Engineering" in match["text"] for match in matches)


def test_soc_fee_query_uses_engineering_and_computing_rows() -> None:
    chunks = load_chunks(Path(__file__).resolve().parents[2] / "data" / "extracted")
    matches = retrieve(
        "What are the fees for SOC?",
        chunks,
        scope=understand_query("What are the fees for SOC?"),
    )
    assert matches
    assert all(match["school_name"] == "School of Computing (SOC)" for match in matches)
    assert any("Aerospace Engineering" in match["text"] for match in matches)


def test_structured_contact_answer_includes_name_and_number() -> None:
    answer = structured_contact_answer(
        [{
            "information_type": "contact_information",
            "text": "Column 2: School of Computing (SOC) | Column 3: Dr. Ramesh Mali | Column 4: 9890032120",
        }]
    )
    assert answer == "School of Computing (SOC): Dr. Ramesh Mali — 9890032120"
