"""The must-cover concept backbone every market curriculum must satisfy.

Each market is free to add more topics, order them, choose depth, and write all
examples itself — but every key below must be covered by at least one level.
"""
from typing import TypedDict


class ConceptDef(TypedDict):
    key: str
    title: str
    description: str


BACKBONE: list[ConceptDef] = [
    {"key": "earning_income", "title": "Earning & income",
     "description": "Where money comes from and the value of work."},
    {"key": "spending_budgeting", "title": "Spending & budgeting",
     "description": "Needs vs wants and making a plan for money."},
    {"key": "saving_goals", "title": "Saving & goals",
     "description": "Setting money aside for short- and long-term goals."},
    {"key": "banking_accounts", "title": "Banking & accounts",
     "description": "Keeping money safe and how accounts work."},
    {"key": "borrowing_debt", "title": "Borrowing & debt",
     "description": "Credit, the interest you pay, and borrowing wisely."},
    {"key": "growing_compound", "title": "Growing money & compound interest",
     "description": "Investing basics and how money grows over time."},
    {"key": "risk_diversification", "title": "Risk & diversification",
     "description": "Why values change and not putting all eggs in one basket."},
    {"key": "safety_scams", "title": "Financial safety & scams",
     "description": "Protecting money and spotting fraud."},
    {"key": "tax_giving", "title": "Tax & giving",
     "description": "How tax works locally and the role of charitable giving."},
]


def backbone_keys() -> set[str]:
    return {c["key"] for c in BACKBONE}
