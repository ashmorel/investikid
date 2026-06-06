import uuid

from pydantic import BaseModel, Field


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class GroupJoinRequest(BaseModel):
    code: str = Field(min_length=1, max_length=12)
    child_user_id: uuid.UUID


class GroupMemberOut(BaseModel):
    child_user_id: uuid.UUID
    username: str


class GroupOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str | None  # only populated for the owner
    is_owner: bool
    members: list[GroupMemberOut]


class GroupLeaderboardEntry(BaseModel):
    username: str
    xp_this_week: int
    is_me: bool


class GroupLeaderboardOut(BaseModel):
    group_id: uuid.UUID
    group_name: str
    entries: list[GroupLeaderboardEntry]
