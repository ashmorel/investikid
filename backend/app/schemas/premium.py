from pydantic import BaseModel, Field


class PremiumRequestIn(BaseModel):
    kind: str = Field(min_length=1, max_length=20)
    label: str = Field(min_length=1, max_length=200)


class PremiumRequestResult(BaseModel):
    status: str  # "sent" | "already_sent" | "no_parent" | "declined"
