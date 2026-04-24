from datetime import date as date_type
from typing import Self

from pydantic import BaseModel, EmailStr, field_validator, model_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    dob: date_type
    country_code: str
    currency_code: str
    parent_email: EmailStr | None = None
    topic_path: str | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.lower().strip()

    @model_validator(mode="after")
    def require_parent_email_for_minors(self) -> Self:
        from datetime import date as d
        today = d.today()
        age = (
            today.year - self.dob.year
            - ((today.month, today.day) < (self.dob.month, self.dob.day))
        )
        if age < 18 and not self.parent_email:
            raise ValueError("parent_email is required for users under 18")
        return self


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
