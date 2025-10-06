from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

try:  # pragma: no cover
    from app.models.models import Purchase, Category  # type: ignore
except Exception:  # pragma: no cover
    Purchase = None  # type: ignore
    Category = None  # type: ignore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _month_bounds(month_str: str) -> Tuple[datetime, datetime]:
    """Return (start, end) datetime bounds for YYYY-MM (end is exclusive)."""
    try:
        start = datetime.strptime(month_str, "%Y-%m")
    except ValueError:
        # Fallback to current month if parsing fails
        today = date.today().replace(day=1)
        start = datetime(today.year, today.month, 1)
    # Compute next month
    if start.month == 12:
        end = datetime(start.year + 1, 1, 1)
    else:
        end = datetime(start.year, start.month + 1, 1)
    return start, end


def _to_float(value: Optional[Any]) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_month_summary(db: Session, *, user_id: int, month: str) -> Dict[str, Any]:
    """Aggregate monthly spend and category breakdown for dashboard.

    Returns a dict shape compatible with routes/service.py BudgetSummaryResponse.
    If models are not ready, returns a safe placeholder result.
    """
    start, end = _month_bounds(month)

    # If models not available yet, return placeholder
    if Purchase is None or Category is None:  # type: ignore
        return {
            "month": month,
            "total_spent": 0.0,
            "by_category": {},
        }

    # Total spent in window
    total_q = (
        db.query(func.coalesce(func.sum(Purchase.amount), 0.0))  # type: ignore[attr-defined]
        .filter(Purchase.user_id == user_id)  # type: ignore[attr-defined]
        .filter(Purchase.occurred_at >= start)  # type: ignore[attr-defined]
        .filter(Purchase.occurred_at < end)  # type: ignore[attr-defined]
    )
    total_spent = _to_float(total_q.scalar())

    # By-category breakdown
    rows = (
        db.query(Category.name, func.coalesce(func.sum(Purchase.amount), 0.0))  # type: ignore[attr-defined]
        .join(Category, Category.id == Purchase.category_id)  # type: ignore[attr-defined]
        .filter(Purchase.user_id == user_id)  # type: ignore[attr-defined]
        .filter(Purchase.occurred_at >= start)  # type: ignore[attr-defined]
        .filter(Purchase.occurred_at < end)  # type: ignore[attr-defined]
        .group_by(Category.name)
        .all()
    )

    by_category: Dict[str, float] = {name: _to_float(total) for name, total in rows}

    return {
        "month": month,
        "total_spent": total_spent,
        "by_category": by_category,
    }


def list_user_categories(db: Session, *, user_id: int) -> List[Dict[str, Any]]:
    """Return basic category info for a user. Placeholder-friendly."""
    if Category is None:  # type: ignore
        return []
    rows = db.query(Category).filter(Category.user_id == user_id).order_by(Category.name.asc()).all()  # type: ignore[attr-defined]
    return [
        {"id": r.id, "name": r.name, "color": getattr(r, "color", None)}
        for r in rows
    ]


def upsert_category(db: Session, *, user_id: int, name: str, color: Optional[str] = None) -> Dict[str, Any]:
    """Create or update a category; returns a dict payload."""
    if Category is None:  # type: ignore
        return {"id": None, "name": name, "color": color}

    row = (
        db.query(Category)  # type: ignore[attr-defined]
        .filter(Category.user_id == user_id, func.lower(Category.name) == name.lower())  # type: ignore[attr-defined]
        .first()
    )
    if row:
        if color is not None:
            setattr(row, "color", color)
    else:
        row = Category(user_id=user_id, name=name, color=color)  # type: ignore[call-arg]
        db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "color": getattr(row, "color", None)}


def add_purchase(
    db: Session,
    *,
    user_id: int,
    amount: float,
    category_id: Optional[int],
    occurred_at: Optional[datetime] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert a new purchase; returns a dict payload. Placeholder-friendly."""
    if Purchase is None:  # type: ignore
        return {
            "id": None,
            "user_id": user_id,
            "amount": float(amount),
            "category_id": category_id,
            "occurred_at": (occurred_at or datetime.utcnow()).isoformat(),
            "note": note,
        }

    row = Purchase(  # type: ignore[call-arg]
        user_id=user_id,
        amount=float(amount),
        category_id=category_id,
        occurred_at=occurred_at or datetime.utcnow(),
        note=note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "user_id": row.user_id,
        "amount": float(row.amount),
        "category_id": row.category_id,
        "occurred_at": getattr(row, "occurred_at", None),
        "note": getattr(row, "note", None),
    }


def list_purchases(
    db: Session,
    *,
    user_id: int,
    month: Optional[str] = None,
    category_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Return purchases for a user (optionally filtered by month/category)."""
    if Purchase is None:  # type: ignore
        return []

    q = db.query(Purchase).filter(Purchase.user_id == user_id)  # type: ignore[attr-defined]

    if month:
        start, end = _month_bounds(month)
        q = q.filter(Purchase.occurred_at >= start).filter(Purchase.occurred_at < end)  # type: ignore[attr-defined]

    if category_id is not None:
        q = q.filter(Purchase.category_id == category_id)  # type: ignore[attr-defined]

    q = q.order_by(Purchase.occurred_at.desc())  # type: ignore[attr-defined]
    rows = q.all()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "amount": float(r.amount),
            "category_id": r.category_id,
            "occurred_at": getattr(r, "occurred_at", None),
            "note": getattr(r, "note", None),
        }
        for r in rows
    ]


__all__ = [
    "get_month_summary",
    "list_user_categories",
    "upsert_category",
    "add_purchase",
    "list_purchases",
]

