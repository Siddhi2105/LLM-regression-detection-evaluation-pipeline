import sys

from src.evaluation.runner import evaluate
from src.evaluation.diff import compare_runs


print("Running baseline evaluation (v1)...")

old_run = evaluate(
    "prompts/v1.yaml",
    "data/golden/golden_dataset.json"
)

print("Baseline accuracy:", old_run["accuracy"])


print("\nRunning new evaluation (v2)...")

new_run = evaluate(
    "prompts/v2.yaml",
    "data/golden/golden_dataset.json"
)

print("New accuracy:", new_run["accuracy"])


print("\nComparing v1 vs v2...")

comparison = compare_runs(old_run, new_run)


print("\n========== REGRESSION CHECK ==========")

print("Old version:", comparison["old_version"])
print("New version:", comparison["new_version"])

print(
    "Old accuracy:",
    round(comparison["old_accuracy"], 4)
)

print(
    "New accuracy:",
    round(comparison["new_accuracy"], 4)
)

print(
    "Accuracy change:",
    round(comparison["accuracy_change"], 4)
)

print("Status:", comparison["status"])
print("Severity:", comparison["severity"])


print("\nChanged cases:")

for case in comparison["changed_cases"]:
    print(
        f"{case['id']}: "
        f"{case['old_prediction']} → "
        f"{case['new_prediction']} "
        f"({case['status']})"
    )


if comparison["severity"] == "critical":
    print("\n❌ CRITICAL REGRESSION")
    print("Pull Request should be blocked.")

    sys.exit(1)


elif comparison["severity"] == "warning":
    print("\n⚠️ WARNING")
    print("Regression detected, but it is below the critical threshold.")

    sys.exit(0)


else:
    print("\n✅ PASS")
    sys.exit(0)