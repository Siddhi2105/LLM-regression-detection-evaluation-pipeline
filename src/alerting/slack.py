import os
import requests
from dotenv import load_dotenv

load_dotenv()


def send_slack_alert(comparison):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url:
        print("Slack webhook URL not configured.")
        return

    message = (
        f"🚨 LLM Regression Detected\n\n"
        f"Old version: {comparison['old_version']}\n"
        f"New version: {comparison['new_version']}\n"
        f"Old accuracy: {comparison['old_accuracy']:.2%}\n"
        f"New accuracy: {comparison['new_accuracy']:.2%}\n"
        f"Accuracy change: {comparison['accuracy_change']:.2%}\n"
        f"Status: {comparison['status']}\n"
        f"Severity: {comparison['severity']}"
    )

    response = requests.post(
        webhook_url,
        json={"text": message},
        timeout=10
    )

    response.raise_for_status()

    print("Slack alert sent successfully.")