from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field


class ClassificationResult(BaseModel):
    category: Literal["billing", "technical", "account", "general"]
    summary: str = Field(min_length=1, max_length=300)


@dataclass
class PromptConfig:
    version: str
    created_at: str
    system_prompt: str
    few_shot_examples: list[dict] = field(default_factory=list)