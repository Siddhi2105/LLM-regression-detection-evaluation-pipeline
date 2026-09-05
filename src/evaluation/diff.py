import json

from src.evaluation.scorer import get_regression_severity
from src.alerting.slack import send_slack_alert


def compare_runs(old_run, new_run):
    old_accuracy = old_run["accuracy"]
    new_accuracy = new_run["accuracy"]

    accuracy_change = new_accuracy - old_accuracy

    if accuracy_change < 0:
        status = "regression"
    elif accuracy_change > 0:
        status = "improvement"
    else:
        status = "no_change"

    severity = get_regression_severity(accuracy_change)

    old_results = {
        result["id"]: result
        for result in old_run["results"]
    }

    new_results = {
        result["id"]: result
        for result in new_run["results"]
    }

    changed_cases = []

    for case_id in old_results:
        old_prediction = old_results[case_id]["predicted_category"]
        new_prediction = new_results[case_id]["predicted_category"]

        if old_prediction != new_prediction:
            expected = old_results[case_id]["expected_category"]

            if (
                old_prediction != expected
                and new_prediction == expected
            ):
                case_status = "fixed"

            elif (
                old_prediction == expected
                and new_prediction != expected
            ):
                case_status = "regression"

            else:
                case_status = "changed"

            changed_cases.append({
                "id": case_id,
                "expected": expected,
                "old_prediction": old_prediction,
                "new_prediction": new_prediction,
                "status": case_status
            })

    return {
        "old_version": old_run["prompt_version"],
        "new_version": new_run["prompt_version"],
        "old_accuracy": old_accuracy,
        "new_accuracy": new_accuracy,
        "accuracy_change": accuracy_change,
        "status": status,
        "severity": severity,
        "changed_cases": changed_cases
    }


if __name__ == "__main__":

    with open(
        "data/results/run_v1_20260905.json",
        "r",
        encoding="utf-8"
    ) as file:
        v1 = json.load(file)

    with open(
        "data/results/run_v2_20260905.json",
        "r",
        encoding="utf-8"
    ) as file:
        v2 = json.load(file)

    comparison = compare_runs(v1, v2)

    print("Old version:", comparison["old_version"])
    print("New version:", comparison["new_version"])
    print("Old accuracy:", comparison["old_accuracy"])
    print("New accuracy:", comparison["new_accuracy"])
    print("Accuracy change:", comparison["accuracy_change"])
    print("Status:", comparison["status"])
    print("Severity:", comparison["severity"])

    fixed = 0
    regressions = 0
    other_changes = 0

    for case in comparison["changed_cases"]:
        if case["status"] == "fixed":
            fixed += 1
        elif case["status"] == "regression":
            regressions += 1
        else:
            other_changes += 1

    print("\nCase changes:")
    print("Fixed:", fixed)
    print("Regressions:", regressions)
    print("Other changes:", other_changes)

    if comparison["changed_cases"]:
        print("\nChanged cases:")

        for case in comparison["changed_cases"]:
            print("\nCase:", case["id"])
            print("Expected:", case["expected"])
            print("Old prediction:", case["old_prediction"])
            print("New prediction:", case["new_prediction"])
            print("Status:", case["status"])
    if comparison["status"] == "regression":
        send_slack_alert(comparison)
    else:
        print("\nNo cases changed.")