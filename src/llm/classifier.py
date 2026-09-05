import os

import yaml
from dotenv import load_dotenv
from openai import OpenAI

from src.models.schema import ClassificationResult, PromptConfig


load_dotenv()


def load_prompt_config(path: str) -> PromptConfig:
    """Load a prompt configuration from a YAML file."""
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
    prompt_config: PromptConfig
) -> ClassificationResult:
    """
    Classify a customer support email.

    In MOCK_LLM mode, a simple keyword-based classifier is used
    for local development and CI testing.

    Otherwise, the real OpenAI model is used.
    """

    # ---------------------------------------------------------
    # MOCK MODE
    # ---------------------------------------------------------
    if os.getenv("MOCK_LLM", "false").lower() == "true":

        email_lower = email.lower()
        version = prompt_config.version

        # -----------------------------------------------------
        # Controlled v2 regression for CI demonstration
        # -----------------------------------------------------
        # This deliberately makes v2 fail emails containing
        # "crashing", so our CI pipeline can demonstrate that
        # a regression is detected.
        if version == "v2":

            if "crashing" in email_lower:
                return ClassificationResult(
                    category="general",
                    summary="Customer has a general question or request.",
                )

        # -----------------------------------------------------
        # ACCOUNT
        # -----------------------------------------------------
        # Account is checked first because an account issue may
        # also contain words such as "payment" or "error".
        if any(
            phrase in email_lower
            for phrase in [
                "password",
                "login",
                "log in",
                "sign in",
                "account",
                "profile",
                "phone number",
                "access my account",
                "regain access",
                "locked",
                "unauthorized",
                "unfamiliar login",
                "don't recognize",
                "do not recognize",
            ]
        ):
            return ClassificationResult(
                category="account",
                summary="Customer has an account-related issue.",
            )

        # -----------------------------------------------------
        # TECHNICAL
        # -----------------------------------------------------
        if any(
            phrase in email_lower
            for phrase in [
                "crash",
                "crashing",
                "error",
                "bug",
                "not working",
                "isn't working",
                "is not working",
                "upload",
                "slow",
                "freezing",
                "freeze",
                "blank",
                "won't load",
                "will not load",
                "can't open",
                "cannot open",
                "search results",
                "results are not showing",
                "reports take",
                "reports page",
                "data appears",
                "none of the data",
                "stuck",
                "processing",
                "loading screen",
                "export",
                "button",
            ]
        ):
            return ClassificationResult(
                category="technical",
                summary="Customer has a technical issue.",
            )

        # -----------------------------------------------------
        # BILLING
        # -----------------------------------------------------
        if any(
            phrase in email_lower
            for phrase in [
                "charged",
                "charge",
                "payment",
                "refund",
                "invoice",
                "subscription",
                "billing",
                "billed",
                "renew",
                "renewal",
                "card",
                "free trial",
                "yearly plan",
                "monthly billing",
            ]
        ):
            return ClassificationResult(
                category="billing",
                summary="Customer has a billing-related issue.",
            )

        # -----------------------------------------------------
        # GENERAL
        # -----------------------------------------------------
        return ClassificationResult(
            category="general",
            summary="Customer has a general question or request.",
        )

    # ---------------------------------------------------------
    # REAL LLM MODE
    # ---------------------------------------------------------

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )

    messages = [
        {
            "role": "system",
            "content": prompt_config.system_prompt,
        }
    ]

    # Add few-shot examples from the YAML prompt
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

    # Add the actual customer email
    messages.append(
        {
            "role": "user",
            "content": email,
        }
    )

    # Ask the OpenAI model for structured output
    response = client.responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        input=messages,
        text_format=ClassificationResult,
    )

    return response.output_parsed