from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator


class Urgency(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Category(str, Enum):
    BUG = "bug"
    BILLING = "billing"
    FEATURE = "feature"
    ONBOARDING = "onboarding"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class TicketRequest(BaseModel):
    ticket_id: str
    text: str


class TriageResult(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    ticket_id: str
    urgency: Urgency
    category: Category
    sentiment: Sentiment
    automation_opportunity: bool
    draft_response: str
    confidence: float
    trace_id: str

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class FeedbackRequest(BaseModel):
    trace_id: str
    score: float
    comment: str | None = None

    @field_validator("score")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        return max(0.0, min(1.0, v))
