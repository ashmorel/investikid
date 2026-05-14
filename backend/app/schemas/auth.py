import re
import uuid
from datetime import date as date_type

from pydantic import BaseModel, EmailStr, Field, field_validator

_COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_TOPIC_RE = re.compile(r"^[a-z0-9_/-]+$")


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(min_length=12, max_length=128)
    dob: date_type
    country_code: str
    currency_code: str
    parent_email: EmailStr | None = None
    topic_path: str | None = Field(default=None, max_length=200)

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("country_code", mode="before")
    @classmethod
    def uppercase_country(cls, v: str) -> str:
        if isinstance(v, str):
            return v.upper().strip()
        return v

    @field_validator("country_code")
    @classmethod
    def validate_country(cls, v: str) -> str:
        if not _COUNTRY_RE.match(v):
            raise ValueError("country_code must be an ISO 3166-1 alpha-2 code")
        return v

    @field_validator("currency_code", mode="before")
    @classmethod
    def uppercase_currency(cls, v: str) -> str:
        if isinstance(v, str):
            return v.upper().strip()
        return v

    @field_validator("currency_code")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if not _CURRENCY_RE.match(v):
            raise ValueError("currency_code must be a 3-letter ISO 4217 code")
        return v

    @field_validator("dob")
    @classmethod
    def validate_dob(cls, v: date_type) -> date_type:
        from datetime import date as d
        today = d.today()
        if v >= today:
            raise ValueError("dob must be in the past")
        age = (
            today.year - v.year
            - ((today.month, today.day) < (v.month, v.day))
        )
        if age < 8:
            raise ValueError("user must be at least 8 years old")
        if age > 120:
            raise ValueError("dob is not plausible")
        return v

    @field_validator("topic_path")
    @classmethod
    def validate_topic(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _TOPIC_RE.match(v):
            raise ValueError("topic_path may only contain [a-z0-9_/-]")
        return v

    # Note: `parent_email` requirement for under-threshold minors is enforced in
    # the /auth/register router using the consent threshold (13 or 16 in select EU
    # countries) rather than a flat <18 schema check, so over-threshold teens can
    # self-register.


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.lower().strip()


class TokenResponse(BaseModel):
    token_type: str = "bearer"
    message: str = "authenticated"


class PendingConsentResponse(BaseModel):
    status: str = "pending_consent"
    user_id: uuid.UUID
