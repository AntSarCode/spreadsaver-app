import os
from typing import Dict, Any, List

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.models.models import Badge


# ---------------------------------------------------------------------------
# DB setup (normalize async URL → sync for this script)
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SPREADSAVER_DATABASE_URL") or "postgresql://postgres:postgres@localhost:5433/postgres"


def _normalize_sync_url(url: str) -> str:
    """Replace async driver prefix so this sync seed script can connect."""
    return url.replace("postgresql+asyncpg://", "postgresql://")


engine = create_engine(_normalize_sync_url(DATABASE_URL), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# ---------------------------------------------------------------------------
# Badge catalog (initial)
# - "criteria" is JSON the evaluation service will interpret later
# ---------------------------------------------------------------------------
BADGE_DATA: List[Dict[str, Any]] = [
    {
        "title": "First Log",
        "description": "Log your very first purchase in SpreadSaver.",
        "icon_url": "badges/first_log.png",
        "criteria": {"purchases_count": 1},
    },
    {
        "title": "Receipt Ranger",
        "description": "Record 10 purchases to build your spending trail.",
        "icon_url": "badges/receipt_ranger.png",
        "criteria": {"purchases_count": 10},
    },
    {
        "title": "Category Explorer",
        "description": "Use 5 different categories in a single month.",
        "icon_url": "badges/category_explorer.png",
        "criteria": {"month_categories_used": 5},
    },
    {
        "title": "No‑Spend Day",
        "description": "Complete one day without logging any purchases.",
        "icon_url": "badges/no_spend_day.png",
        "criteria": {"no_spend_days": 1},
    },
    {
        "title": "No‑Spend Streak",
        "description": "Achieve a 3‑day no‑spend streak.",
        "icon_url": "badges/no_spend_streak.png",
        "criteria": {"no_spend_streak": 3},
    },
    {
        "title": "Rule Runner",
        "description": "Enable a budget rule set (e.g., 50/30/20).",
        "icon_url": "badges/rule_runner.png",
        "criteria": {"rules_enabled": True},
    },
    {
        "title": "Under Budget",
        "description": "Finish a month at or below your planned budget.",
        "icon_url": "badges/under_budget.png",
        "criteria": {"under_budget_ratio": 1.0},  # actual spend / budget <= 1.0
    },
    {
        "title": "Saver Spark",
        "description": "Save at least $100 in a single month.",
        "icon_url": "badges/saver_spark.png",
        "criteria": {"month_savings_amount": 100},
    },
    {
        "title": "Savings Streak",
        "description": "Save money 3 months in a row.",
        "icon_url": "badges/savings_streak.png",
        "criteria": {"months_saving_streak": 3},
    },
    {
        "title": "Debt Chopper",
        "description": "Pay down $200 of debt in a single month.",
        "icon_url": "badges/debt_chopper.png",
        "criteria": {"month_debt_payment": 200},
    },
    {
        "title": "Group Buddy",
        "description": "Join or create a budgeting group.",
        "icon_url": "badges/group_buddy.png",
        "criteria": {"groups_joined": 1},
    },
    {
        "title": "Badge Collector",
        "description": "Earn 5 different SpreadSaver badges.",
        "icon_url": "badges/badge_collector.png",
        "criteria": {"badges_earned_count": 5},
    },
]


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------

def upsert_badge(db: Session, data: Dict[str, Any]) -> None:
    existing = db.query(Badge).filter(Badge.title == data["title"]).first()
    if existing:
        # Update descriptive fields & criteria, keep same identity
        existing.description = data.get("description", existing.description)
        existing.icon_url = data.get("icon_url", existing.icon_url)
        if "criteria" in data:
            existing.criteria = data["criteria"]
    else:
        db.add(Badge(**data))


def seed_badges() -> None:
    db: Session = SessionLocal()
    try:
        for row in BADGE_DATA:
            upsert_badge(db, row)
        db.commit()
        print(f"Seeded/updated {len(BADGE_DATA)} badges.")
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error seeding badges: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_badges()
