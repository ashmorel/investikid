import uuid

from pydantic import BaseModel, ConfigDict


class ActiveMissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    lesson_id: uuid.UUID
    mission_type: str
    title: str
    prompt: str
    params_json: dict
