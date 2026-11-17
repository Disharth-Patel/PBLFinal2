import json
import math
import re
from pathlib import Path

import httpx


SUPPORTED_SCHOOLS = (
    "School of Fine Arts and Applied Arts (SOFA)",
    "Institute of Design (IOD)",
    "School of Architecture (SOA)",
    "School of Computing (SOC)",
)


def load_chunks(extracted_directory: Path, chunk_size: int = 1200, overlap: int = 180) -> list[dict[str, object]]:
    chunks: list[dict[str, object]] = []
    for path in sorted(extracted_directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = _records(payload)
        for source, location, text in records:
            clean = re.sub(r"\s+", " ", text).strip()
            for start in range(0, len(clean), max(1, chunk_size - overlap)):
                part = clean[start : start + chunk_size]
                if part:
                    chunks.append(_metadata(source, location, part))
                if start + chunk_size >= len(clean):
                    break
    return chunks


def _records(payload: dict) -> list[tuple[str, str, str]]:
    source = payload["source"]
    format_name = payload["format"]
    if format_name == "PDF":
        return [(source, f"page {page['page']}", page["text"]) for page in payload["pages"]]
    if format_name == "XLSX":
        records: list[tuple[str, str, str]] = []
        for sheet in payload["sheets"]:
            rows = sheet["rows"]
            if not rows:
                continue
            headers = [
                str(value).strip() if value is not None else f"Column {index + 1}"
                for index, value in enumerate(rows[0])
            ]
            for index, row in enumerate(rows[1:], start=2):
                values = [
                    f"{headers[column]}: {value}"
                    for column, value in enumerate(row)
                    if value is not None and str(value).strip()
                ]
                if values:
                    records.append((source, f"sheet {sheet['name']} row {index}", " | ".join(values)))
        return records
    if format_name == "PPTX":
        return [(source, f"slide {slide['slide']}", slide["text"]) for slide in payload["slides"]]
    if format_name == "DOCX":
        return [(source, f"paragraphs {index + 1}", text) for index, text in enumerate(payload["paragraphs"])]
    if format_name == "JSON":
        data = payload["data"]
        if isinstance(data, dict) and isinstance(data.get("courses"), list):
            records = [
                (source, f"course {index + 1}", json.dumps(course, ensure_ascii=False))
                for index, course in enumerate(data["courses"])
            ]
            notes = data.get("data_notes", [])
            if notes:
                records.append((source, "data notes", " ".join(str(note) for note in notes)))
            return records
        return [(source, "document", json.dumps(data, ensure_ascii=False))]
    return [(source, "document", payload.get("text", ""))]


def _metadata(source: str, location: str, text: str) -> dict[str, object]:
    lower_source = source.lower()
    lower_text = text.lower()
    school = None
    aliases = {
        "school of fine arts and applied arts": SUPPORTED_SCHOOLS[0],
        "sofa": SUPPORTED_SCHOOLS[0],
        "institute of design": SUPPORTED_SCHOOLS[1],
        "iod": SUPPORTED_SCHOOLS[1],
        "school of architecture": SUPPORTED_SCHOOLS[2],
        "soa": SUPPORTED_SCHOOLS[2],
        "school of computing": SUPPORTED_SCHOOLS[3],
        "soc": SUPPORTED_SCHOOLS[3],
    }
    source_is_directory = "contact_directory" in lower_source and "row " in location.lower()
    for alias, value in aliases.items():
        if alias in lower_source or (source_is_directory and alias in lower_text):
            school = value
            break
    if "sap_brochure" in lower_source:
        school = SUPPORTED_SCHOOLS[2]
    elif "mitid" in lower_source:
        school = SUPPORTED_SCHOOLS[1]
    if "soc" in lower_source:
        school = SUPPORTED_SCHOOLS[3]
    elif "engineering & computing" in lower_text or "engineering and computing" in lower_text:
        school = SUPPORTED_SCHOOLS[3]
    elif re.search(r"\barchitecture\b|\bb\.arch\b", lower_text):
        school = SUPPORTED_SCHOOLS[2]
    information_type = "general"
    fee_sheet = any(sheet_name in location.lower() for sheet_name in ("all courses", "additional charges"))
    if "fee" in lower_source and (fee_sheet or lower_source.endswith(".json")):
        information_type = "fees"
    if source_is_directory:
        information_type = "contact_information"
    for keyword, category in (
        ("eligibility", "eligibility"),
        ("admission process", "admission_process"),
        ("application", "application_procedure"),
        ("fee", "fees"),
        ("scholarship", "scholarships"),
        ("contact", "contact_information"),
    ):
        if keyword in lower_text and (category != "fees" or fee_sheet):
            information_type = category
            break
    institution = "MIT Art, Design and Technology University" if "mit" in lower_text or "mit" in lower_source else None
    return {
        "source": source,
        "location": location,
        "source_document": source,
        "source_page": location,
        "document_id": source,
        "document_version": None,
        "institution_name": institution,
        "school_name": school,
        "department_name": None,
        "programme_name": None,
        "admission_category": None,
        "information_type": information_type,
        "academic_year": "2026" if "2026" in source else None,
        "text": text,
    }


def understand_query(query: str, history: list[dict[str, str]] | None = None) -> dict[str, str | None]:
    text = " ".join([*(item["content"] for item in (history or [])[-6:]), query]).lower()
    scope = query.lower()
    school = None
    for alias, value in (
        ("school of fine arts", SUPPORTED_SCHOOLS[0]),
        ("sofa", SUPPORTED_SCHOOLS[0]),
        ("institute of design", SUPPORTED_SCHOOLS[1]),
        ("iod", SUPPORTED_SCHOOLS[1]),
        ("school of architecture", SUPPORTED_SCHOOLS[2]),
        ("soa", SUPPORTED_SCHOOLS[2]),
        ("school of computing", SUPPORTED_SCHOOLS[3]),
        ("soc", SUPPORTED_SCHOOLS[3]),
    ):
        if alias in scope:
            school = value
            break
    if not school and re.search(r"\bb\.?\s*arch\b|\barchitecture\b", scope):
        school = SUPPORTED_SCHOOLS[2]
    if not school:
        for alias, value in (("school of computing", SUPPORTED_SCHOOLS[3]), ("soc", SUPPORTED_SCHOOLS[3])):
            if alias in text:
                school = value
                break
    category = "general"
    for keyword, value in (("eligib", "eligibility"), ("fee", "fees"), ("scholar", "scholarships"), ("contact", "contact_information"), ("admission", "admission_process"), ("apply", "application_procedure")):
        if keyword in query.lower():
            category = value
            break
    return {"school_name": school, "programme_name": None, "information_type": category}


def _matches_scope(chunk: dict[str, object], scope: dict[str, str | None]) -> bool:
    requested_school = scope.get("school_name")
    if requested_school and chunk.get("school_name") != requested_school:
        return False
    requested_type = scope.get("information_type")
    return not requested_type or requested_type == "general" or chunk.get("information_type") == requested_type


def retrieve(query: str, chunks: list[dict[str, object]], limit: int = 5, scope: dict[str, str | None] | None = None) -> list[dict[str, object]]:
    normalized_query = re.sub(r"\s+", " ", query.lower()).strip()
    terms = set(re.findall(r"\w+", normalized_query))
    phrases = [
        " ".join(pair)
        for pair in zip(normalized_query.split()[:-1], normalized_query.split()[1:])
        if len(pair[0]) > 2 and len(pair[1]) > 2
    ]
    scored = []
    for chunk in chunks:
        if scope and not _matches_scope(chunk, scope):
            continue
        chunk_text = re.sub(r"\s+", " ", chunk["text"].lower())
        words = set(re.findall(r"\w+", chunk_text))
        score = len(terms & words) / max(1, len(terms))
        score += sum(0.2 for phrase in phrases if phrase in chunk_text)
        if scope and scope.get("information_type") != "general" and chunk.get("information_type") == scope["information_type"]:
            score += 0.15
        if (
            score == 0
            and scope
            and scope.get("information_type") != "general"
            and scope.get("information_type") == chunk.get("information_type")
        ):
            score = 0.15
        if score:
            scored.append((score, chunk))
    return [{**chunk, "score": score} for score, chunk in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


async def embed_texts(base_url: str, model: str, texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=120) as client:
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), 64):
            batch = texts[start : start + 64]
            response = await client.post(
                f"{base_url.rstrip('/')}/api/embed",
                json={"model": model, "input": batch},
            )
            response.raise_for_status()
            payload = response.json()
            batch_embeddings = payload.get("embeddings", [])
            if len(batch_embeddings) != len(batch):
                raise RuntimeError("Embedding service returned an incomplete batch")
            embeddings.extend(batch_embeddings)
        return embeddings


def save_index(path: Path, chunks: list[dict[str, object]], embeddings: list[list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"chunks": chunks, "embeddings": embeddings}, ensure_ascii=False), encoding="utf-8")


def load_index(path: Path) -> dict:
    if not path.exists():
        return {"chunks": [], "embeddings": []}
    index = json.loads(path.read_text(encoding="utf-8"))
    index["chunks"] = [_metadata(chunk["source"], chunk["location"], chunk["text"]) | {key: value for key, value in chunk.items() if key not in {"source", "location", "text"}} for chunk in index.get("chunks", [])]
    return index


def vector_retrieve(query_embedding: list[float], index: dict, limit: int = 5, scope: dict[str, str | None] | None = None) -> list[dict]:
    scored = []
    for chunk, embedding in zip(index["chunks"], index["embeddings"]):
        if scope and not _matches_scope(chunk, scope):
            continue
        score = _cosine(query_embedding, embedding)
        scored.append((score, chunk))
    return [{**chunk, "score": score} for score, chunk in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


def _cosine(left: list[float], right: list[float]) -> float:
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(sum(value * value for value in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0


def grounded_prompt(question: str, context: list[dict[str, object]], history: list[dict[str, str]], scope: dict[str, str | None] | None = None) -> str:
    context_text = "\n\n".join(
        f"[{item['source']} {item['location']} | school={item.get('school_name') or 'unassigned'} | type={item.get('information_type')}]\n{item['text']}"
        for item in context
    )
    return (
        "You are a careful admissions assistant. Answer only from verified context. "
        "Never mix schools, programmes, academic years, admission categories, fees, eligibility, or contacts. "
        "If a school is requested, use only chunks belonging to that school. If the context does not contain the answer, say: "
        "\"I couldn't find verified information about this specific query in the available institutional records. Please contact the relevant admission department for confirmation.\" "
        "Never invent institutional facts or use general model knowledge.\n\n"
        f"RESOLVED QUERY SCOPE:\n{json.dumps(scope or {})}\n\n"
        f"VERIFIED CONTEXT:\n{context_text or '(no matching verified context)'}\n\n"
        f"CONVERSATION:\n{json.dumps(history[-6:])}\n\nQUESTION: {question}"
    )


def structured_contact_answer(context: list[dict[str, object]]) -> str | None:
    contacts: list[str] = []
    pattern = re.compile(
        r"Column 2:\s*(?P<institution>.*?)\s*\|\s*Column 3:\s*(?P<person>.*?)\s*\|\s*Column 4:\s*(?P<number>[^|]+)"
    )
    for item in context:
        if item.get("information_type") != "contact_information":
            continue
        match = pattern.search(str(item.get("text", "")))
        if match:
            contacts.append(
                f"{match.group('institution').strip()}: "
                f"{match.group('person').strip()} — {match.group('number').strip()}"
            )
    return "\n".join(contacts) if contacts else None


async def generate_answer(
    base_url: str,
    model: str,
    question: str,
    context: list[dict[str, object]],
    history: list[dict[str, str]],
    scope: dict[str, str | None] | None = None,
    temperature: float = 0.0,
    top_p: float = 1.0,
    context_length: int = 4096,
    max_tokens: int = 512,
) -> str:
    prompt = grounded_prompt(question, context, history, scope)
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "num_ctx": context_length,
                    "num_predict": max_tokens,
                },
            },
        )
        response.raise_for_status()
        return response.json().get("response", "I could not generate a response.")
