from pydantic import BaseModel


class ParentPreferencesOut(BaseModel):
    trial_reminder_opt_out: bool
    weekly_digest_opt_out: bool


class ParentPreferencesUpdate(BaseModel):
    trial_reminder_opt_out: bool | None = None
    weekly_digest_opt_out: bool | None = None
