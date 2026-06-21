from pydantic import BaseModel, Field


class LevelNode(BaseModel):
    title: str
    order_index: int
    complexity_tier: int = Field(ge=1, le=3)
    learning_objective: str
    concepts: list[str]
    backbone_keys: list[str] = []
    level_id: str | None = None


class ModuleNode(BaseModel):
    topic: str
    title: str
    icon: str = "📚"
    min_age: int = 10
    max_age: int = 16
    order_index: int
    levels: list[LevelNode]


class CurriculumProposal(BaseModel):
    market_code: str
    modules: list[ModuleNode]


class ValidationReport(BaseModel):
    ok: bool
    missing_backbone: list[str]
    tiers_present: list[int]
    spans_all_tiers: bool
    regressions: list[str]
