import uuid
from datetime import date, datetime

from pydantic import BaseModel


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
    topic_path: str | None = None
