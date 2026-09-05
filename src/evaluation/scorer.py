def calculate_accuracy(results):
    if not results:
        return 0.0

    correct = sum(
        1 for result in results
        if result["correct"]
    )

    return correct / len(results)


def calculate_error_rate(results):
    if not results:
        return 0.0

    incorrect = sum(
        1 for result in results
        if not result["correct"]
    )

    return incorrect / len(results)

def get_regression_severity(accuracy_change):
    drop = -accuracy_change

    if drop < 0.03:
        return "pass"

    elif drop <= 0.08:
        return "warning"

    else:
        return "critical"