import json
from pathlib import Path

from app.services.rag import load_chunks, retrieve, understand_query


def build_dataset(extracted_directory: Path, output_path: Path) -> dict[str, int | str]:
    chunks = load_chunks(extracted_directory)
    examples = []
    for chunk in chunks[:100]:
        school = chunk.get("school_name")
        question = f"What information is provided in {chunk['location']}?"
        if school:
            question = f"What information is provided by {school} in {chunk['location']}?"
        examples.append(
            {
                "question": question,
                "answer": chunk["text"],
                "source": chunk["source"],
                "location": chunk["location"],
                "school_name": school,
                "information_type": chunk.get("information_type"),
            }
        )
    fee_cases = (
        ("What is the Aerospace Engineering fee for 2026-27?", "Aerospace Engineering"),
        ("What is the total fee for the B.Des course?", "Course: B.Des |"),
        ("What is the hostel charge for Marine Engineering?", "Marine Engineering hostel"),
    )
    for question, marker in fee_cases:
        fee_chunk = next(
            (
                chunk
                for chunk in chunks
                if chunk["source"] == "MIT_ADT_University_Fees_2026-27.xlsx"
                and marker.lower() in chunk["text"].lower()
            ),
            None,
        )
        if fee_chunk:
            examples.append(
                {
                    "question": question,
                    "answer": fee_chunk["text"],
                    "source": fee_chunk["source"],
                    "location": fee_chunk["location"],
                    "school_name": fee_chunk.get("school_name"),
                    "information_type": "fees",
                }
            )
    examples.append(
        {
            "question": "What is the verified zxqv plmno krstj?",
            "answer": "",
            "source": None,
            "location": None,
            "answerable": False,
            "retrieval_query": "zxqv plmno krstj",
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for example in examples:
            file.write(json.dumps(example, ensure_ascii=False) + "\n")
    return {"examples": len(examples), "output_path": str(output_path), "status": "generated"}


def evaluate_retrieval(dataset_path: Path, extracted_directory: Path) -> dict[str, float | int | str]:
    if not dataset_path.exists():
        return {"cases": 0, "hit_rate": 0.0, "unavailable_precision": 0.0, "status": "dataset-missing"}
    cases = [json.loads(line) for line in dataset_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    hits = 0
    unavailable_correct = 0
    unavailable_cases = 0
    attribution_correct = 0
    attribution_cases = 0
    contamination_cases = 0
    for case in cases:
        question = case.get("retrieval_query", case["question"])
        scope = understand_query(question)
        matches = retrieve(question, load_chunks(extracted_directory), 5, scope)
        answerable = case.get("answerable", True)
        if not answerable:
            unavailable_cases += 1
            if not matches:
                unavailable_correct += 1
        elif any(match["source"] == case["source"] and match["location"] == case["location"] for match in matches):
            hits += 1
        expected_school = case.get("school_name")
        if expected_school and scope.get("school_name"):
            attribution_cases += 1
            if matches and all(match.get("school_name") == expected_school for match in matches):
                attribution_correct += 1
            if any(match.get("school_name") != expected_school for match in matches):
                contamination_cases += 1
    answerable_cases = len(cases) - unavailable_cases
    return {
        "cases": len(cases),
        "answerable_cases": answerable_cases,
        "hit_rate": hits / answerable_cases if answerable_cases else 0.0,
        "unavailable_cases": unavailable_cases,
        "unavailable_precision": unavailable_correct / unavailable_cases if unavailable_cases else 0.0,
        "school_attribution_accuracy": attribution_correct / attribution_cases if attribution_cases else 1.0,
        "cross_school_contamination_rate": contamination_cases / attribution_cases if attribution_cases else 0.0,
        "status": "evaluated",
    }
