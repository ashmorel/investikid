import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class ParentMagicLinkRequest(BaseModel):
    email: EmailStr


class ChildOut(BaseModel):
    user_id: uuid.UUID
    username: str
    country_code: str
    is_active: bool
    is_premium: bool
    parent_consent_given_at: datetime | None
    consent_declined_at: datetime | None
    deleted_at: datetime | None
    deletion_requested_at: datetime | None


class FreezeRequest(BaseModel):
    frozen: bool


class PremiumToggleRequest(BaseModel):
    premium: bool
