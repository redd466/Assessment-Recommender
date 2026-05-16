from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1)


class Recommendation(BaseModel):
    name: str
    url: str
    test_type: str


class ChatResponse(BaseModel):
    reply: str
    recommendations: list[Recommendation]
    end_of_conversation: bool


class CatalogItem(BaseModel):
    name: str
    url: str
    test_type: str
    description: str = ""
    job_levels: list[str] = []
    languages: list[str] = []
    assessment_length_minutes: int | None = None
    remote_testing: bool | None = None
    adaptive_irt: bool | None = None
