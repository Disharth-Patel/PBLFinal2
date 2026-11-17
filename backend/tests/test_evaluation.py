import json
from pathlib import Path

from app.services.evaluation import build_dataset, evaluate_retrieval


def test_evaluation_dataset_and_metric(tmp_path: Path) -> None:
    extracted = Path(__file__).resolve().parents[2] / "data" / "extracted"
    dataset = tmp_path / "evaluation.jsonl"

    result = build_dataset(extracted, dataset)
    metric = evaluate_retrieval(dataset, extracted)

    assert result["examples"] > 0
    assert metric["cases"] == result["examples"]
    assert metric["answerable_cases"] == result["examples"] - 1
    assert metric["unavailable_precision"] == 1.0
    assert 0.0 <= metric["school_attribution_accuracy"] <= 1.0
    assert metric["cross_school_contamination_rate"] == 0.0
    assert 0.0 <= metric["hit_rate"] <= 1.0
    assert json.loads(dataset.read_text(encoding="utf-8").splitlines()[0])["source"]
    cases = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
    fee_cases = [case for case in cases if case.get("information_type") == "fees"]
    assert len(fee_cases) >= 3
    assert any("Aerospace Engineering" in case["question"] for case in fee_cases)
    assert any("B.Des" in case["question"] for case in fee_cases)
    assert any("hostel" in case["question"] for case in fee_cases)
    assert metric["hit_rate"] > 0.0
