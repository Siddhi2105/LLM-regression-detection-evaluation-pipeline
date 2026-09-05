import os

import yaml
from dotenv import load_dotenv
from openai import OpenAI

from src.models.schema import ClassificationResult, PromptConfig


load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def load_prompt_config(path: str) -> PromptConfig:
    with open(path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    return PromptConfig(
        version=data["version"],
        created_at=data["created_at"],
        system_prompt=data["system_prompt"],
        few_shot_examples=data.get("few_shot_examples", []),
    )


def classify_email(
    email: str,
    prompt_config: PromptConfig,
) -> ClassificationResult:

    # Development mode: don't call the real LLM
    if os.getenv("MOCK_LLM", "false").lower() == "true":
        email_lower = email.lower()
        version = prompt_config.version

        # Controlled v2 regression:
        # In v2, deliberately misclassify the crashing case.
        if version == "v2":
            if "crashing" in email_lower:
                return ClassificationResult(
                    category="general",
                    summary="Customer has a general question or request.",
                )

        if any(
    word in email_lower
    for word in [
        "charged",
        "payment",
        "refund",
        "invoice",
        "subscription",
        "declined",
        "renew",
        "card",
    ]
):
            return ClassificationResult(
                category="billing",
                summary="Customer has a billing-related issue.",
            )

        if any(
    word in email_lower
    for word in [
        "crash",
        "error",
        "bug",
        "not working",
        "upload",
        "slow",
        "blank",
        "export",
        "button",
        "stuck",
    ]
):
            return ClassificationResult(
                category="technical",
                summary="Customer has a technical issue.",
            )

        if any(
            word in email_lower
            for word in [
                "password",
                "login",
                "log in",
                "account",
                "profile",
            ]
        ):
            return ClassificationResult(
                category="account",
                summary="Customer has an account-related issue.",
            )

        return ClassificationResult(
            category="general",
            summary="Customer has a general question or request.",
        )

    # Real LLM mode
    messages = [
        {
            "role": "system",
            "content": prompt_config.system_prompt,
        }
    ]

    for example in prompt_config.few_shot_examples:
        messages.append(
            {
                "role": "user",
                "content": example["input"],
            }
        )

        messages.append(
            {
                "role": "assistant",
                "content": (
                    f'Category: {example["output"]["category"]}\n'
                    f'Summary: {example["output"]["summary"]}'
                ),
            }
        )

    messages.append(
        {
            "role": "user",
            "content": email,
        }
    )

    response = client.responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        input=messages,
        text_format=ClassificationResult,
    )

    return response.output_parsed