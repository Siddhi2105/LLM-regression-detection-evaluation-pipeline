import json
import os
from datetime import datetime

from src.llm.classifier import classify_email, load_prompt_config
from src.evaluation.scorer import calculate_accuracy, calculate_error_rate


def load_golden_dataset(path: str):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

def save_results(evaluation, output_dir="data/results"):
    os.makedirs(output_dir, exist_ok=True)

    date = datetime.now().strftime("%Y%m%d")

    filename = (
        f"run_{evaluation['prompt_version']}_{date}.json"
    )

    path = os.path.join(output_dir, filename)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(evaluation, file, indent=2)

    return path


def evaluate(prompt_path: str, dataset_path: str):
    prompt_config = load_prompt_config(prompt_path)
    dataset = load_golden_dataset(dataset_path)

    results = []
    correct = 0

    for case in dataset:
        prediction = classify_email(
            case["email"],
            prompt_config
        )

        is_correct = (
            prediction.category == case["expected_category"]
        )

        if is_correct:
            correct += 1

        results.append({
            "id": case["id"],
            "email": case["email"],
            "expected_category": case["expected_category"],
            "predicted_category": prediction.category,
            "expected_summary": case["expected_summary"],
            "predicted_summary": prediction.summary,
            "correct": is_correct
        })

    accuracy = calculate_accuracy(results)
    error_rate = calculate_error_rate(results)
    return {
        "prompt_version": prompt_config.version,
        "total_cases": len(dataset),
        "correct": correct,
        "incorrect": len(dataset) - correct,
        "accuracy": accuracy,
        "error_rate": error_rate,
        "results": results
    }


if __name__ == "__main__":
    evaluation = evaluate(
        "prompts/v2.yaml",
        "data/golden/golden_dataset.json"
    )

    saved_path = save_results(evaluation)

    print("Results saved to:", saved_path)

    print("Prompt version:", evaluation["prompt_version"])
    print("Total cases:", evaluation["total_cases"])
    print("Correct:", evaluation["correct"])
    print("Incorrect:", evaluation["incorrect"])
    print("Accuracy:", evaluation["accuracy"])
    print("Error rate:", evaluation["error_rate"])

    print("\nIncorrect cases:")

    for result in evaluation["results"]:
        if not result["correct"]:
            print("\nCase:", result["id"])
            print("Email:", result["email"])
            print("Expected:", result["expected_category"])
            print("Predicted:", result["predicted_category"])