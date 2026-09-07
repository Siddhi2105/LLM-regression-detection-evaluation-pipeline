from src.evaluation.diff import compare_runs


def test_detects_regression():
    old_run = {
        "prompt_version": "v1",
        "accuracy": 0.95,
        "results": [
            {
                "id": "001",
                "expected_category": "billing",
                "predicted_category": "billing"
            }
        ]
    }

    new_run = {
        "prompt_version": "v2",
        "accuracy": 0.90,
        "results": [
            {
                "id": "001",
                "expected_category": "billing",
                "predicted_category": "general"
            }
        ]
    }

    comparison = compare_runs(old_run, new_run)

    assert comparison["status"] == "regression"
    assert comparison["severity"] == "warning"
    assert round(comparison["accuracy_change"], 2) == -0.05
    assert len(comparison["changed_cases"]) == 1

