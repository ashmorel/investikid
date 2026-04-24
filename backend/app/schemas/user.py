import re
import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

_COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_TOPIC_RE = re.compile(r"^[a-z0-9_/-]+$")


class UserProfile(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    dob: date
    country_code: str
    currency_code: str
    topic_path: str | None
    is_premium: bool
    parent_email: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdatePreferencesRequest(BaseModel):
    country_code: str | None = None
    currency_code: str | None = None
    topic_path: str | None = Field(default=None, max_length=200)

    @field_validator("country_code", mode="before")
    @classmethod
    def uppercase_country(cls, v):
        if isinstance(v, str):
            return v.upper().strip()
        return v

    @field_validator("country_code")
    @classmethod
    def validate_country(cls, v):
        if v is None:
            return v
        if not _COUNTRY_RE.match(v):
            raise ValueError("country_code must be an ISO 3166-1 alpha-2 code")
        return v

    @field_validator("currency_code", mode="before")
    @classmethod
    def uppercase_currency(cls, v):
        if isinstance(v, str):
            return v.upper().strip()
        return v

    @field_validator("currency_code")
    @classmethod
    def validate_currency(cls, v):
        if v is None:
            return v
        if not _CURRENCY_RE.match(v):
            raise ValueError("currency_code must be a 3-letter ISO 4217 code")
        return v

    @field_validator("topic_path")
    @classmethod
    def validate_topic(cls, v):
        if v is None:
            return v
        if not _TOPIC_RE.match(v):
            raise ValueError("topic_path may only contain [a-z0-9_/-]")
        return v
