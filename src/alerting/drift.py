import json
import glob


def load_accuracies(results_dir="data/results"):
    """
    Read accuracy values from all evaluation result files.
    """

    files = sorted(
        glob.glob(f"{results_dir}/*.json")
    )

    accuracies = []

    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        accuracies.append({
            "file": file_path,
            "accuracy": data["accuracy"]
        })

    return accuracies


def detect_drift(accuracies, window=7, threshold=0.03):

    if len(accuracies) < window:
        return {
            "drift_detected": False,
            "message": f"Need at least {window} runs to detect drift."
        }

    recent = accuracies[-window:]

    first = recent[0]["accuracy"]
    last = recent[-1]["accuracy"]

    change = last - first

    if change <= -threshold:
        return {
            "drift_detected": True,
            "change": change,
            "start_accuracy": first,
            "end_accuracy": last,
            "message": "Performance drift detected."
        }

    return {
        "drift_detected": False,
        "change": change,
        "start_accuracy": first,
        "end_accuracy": last,
        "message": "No significant drift detected."
    }


if __name__ == "__main__":

    results = load_accuracies()

    print("Evaluation runs found:", len(results))

    for result in results:
        print(
            result["file"],
            "→",
            result["accuracy"]
        )

    drift = detect_drift(results)

    print("\nDrift detected:", drift["drift_detected"])
    print("Message:", drift["message"])

    if "change" in drift:
        print(
            "Change:",
            round(drift["change"], 4)
        )