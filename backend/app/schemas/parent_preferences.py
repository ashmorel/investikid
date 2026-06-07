from pydantic import BaseModel


class ParentPreferencesOut(BaseModel):
    trial_reminder_opt_out: bool


class ParentPreferencesUpdate(BaseModel):
    trial_reminder_opt_out: bool
