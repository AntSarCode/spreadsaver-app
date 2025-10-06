# /backend/app/utils/calculations.py
# SpreadSaver – Budget math helpers
# NOTE: Floats are used for simplicity. For high-precision money math, consider Decimal.

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

Number = Union[int, float]


# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------

def to_float(value: Optional[Number]) -> float:
    """Safely coerce a value to float, returning 0.0 on failure/None."""
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def month_key(dt: Union[date, datetime, str]) -> str:
    """Return YYYY-MM from a date/datetime or passthrough if already that shape."""
    if isinstance(dt, str) and len(dt) == 7 and dt.count("-") == 1:
        return dt
    if isinstance(dt, datetime):
        return f"{dt.year:04d}-{dt.month:02d}"
    if isinstance(dt, date):
        return f"{dt.year:04d}-{dt.month:02d}"
    raise ValueError("Unsupported type for month_key")


# ---------------------------------------------------------------------------
# Allocation rules & compliance
# ---------------------------------------------------------------------------

def normalize_rules(
    rules: Optional[Mapping[str, Number]] = None,
    *,
    default: Optional[Mapping[str, Number]] = None,
) -> Dict[str, float]:
    """Normalize allocation rules to fractional weights that sum to <= 1.0.

    - Accepts percentages (e.g., 50, 30) or fraction (0.5, 0.3) or fixed amounts (negative values unsupported).
    - If total > 1.0 and all values > 1, treat as percentages (divide by 100).
    - Unspecified remainder is left for "Unallocated".
    """
    src = dict(default or {"Needs": 0.5, "Wants": 0.3, "Savings": 0.2})
    if rules:
        src.update(rules)

    values = list(src.values())
    # If looks like percentages (sum > 1 and values are mostly >1), convert to 0..1
    if sum(v for v in values if v is not None) > 1.0 and all(to_float(v) >= 1.0 for v in values):
        src = {k: to_float(v) / 100.0 for k, v in src.items()}
    else:
        src = {k: to_float(v) for k, v in src.items()}

    # Cap negatives at 0
    for k in list(src.keys()):
        if src[k] < 0:
            src[k] = 0.0

    return src


def allocate_budget(
    income: Number,
    rules: Optional[Mapping[str, Number]] = None,
) -> Dict[str, float]:
    """Allocate income by rule fractions (50/30/20 default). Returns dollars per category.

    Any remainder (if rules sum < 1) is added to 'Unallocated'. If rules sum > 1, values are scale-normalized.
    """
    income_f = to_float(income)
    fracs = normalize_rules(rules)

    total = sum(fracs.values())
    alloc: Dict[str, float] = {}

    if total == 0:
        return {"Unallocated": income_f}

    if total > 1.0:
        # Normalize down proportionally
        fracs = {k: v / total for k, v in fracs.items()}

    for k, v in fracs.items():
        alloc[k] = round(income_f * v, 2)

    remainder = round(income_f - sum(alloc.values()), 2)
    if remainder != 0:
        alloc["Unallocated"] = alloc.get("Unallocated", 0.0) + remainder

    return alloc


def compliance_report(
    planned: Mapping[str, Number],
    actual: Mapping[str, Number],
) -> Dict[str, Union[float, Dict[str, float], List[str]]]:
    """Compare planned allocation vs actual spend by category.

    Returns a dict with: total_planned, total_actual, compliance_ratio, overruns, underruns.
    """
    p = {k: to_float(v) for k, v in planned.items()}
    a = {k: to_float(v) for k, v in actual.items()}

    categories = set(p.keys()) | set(a.keys())
    overruns: Dict[str, float] = {}
    underruns: Dict[str, float] = {}

    total_p = sum(p.values())
    total_a = sum(a.values())

    for cat in categories:
        dv = a.get(cat, 0.0) - p.get(cat, 0.0)
        if dv > 0:
            overruns[cat] = round(dv, 2)
        elif dv < 0:
            underruns[cat] = round(-dv, 2)

    compliance = 1.0 if total_p == 0 else round(min(total_a / total_p, 9.99), 4)

    return {
        "total_planned": round(total_p, 2),
        "total_actual": round(total_a, 2),
        "compliance_ratio": compliance,
        "overruns": overruns,
        "underruns": underruns,
    }


# ---------------------------------------------------------------------------
# Purchase aggregations
# ---------------------------------------------------------------------------

def aggregate_by_category(
    purchases: Sequence[Mapping[str, Union[str, Number]]],
    *,
    category_key: str = "category",
    amount_key: str = "amount",
) -> Dict[str, float]:
    """Aggregate a list of purchase dicts by category → total amount."""
    totals: Dict[str, float] = defaultdict(float)
    for row in purchases:
        cat = str(row.get(category_key) or "Unknown")
        amt = to_float(row.get(amount_key))
        totals[cat] += amt
    return {k: round(v, 2) for k, v in totals.items()}


def aggregate_by_month(
    purchases: Sequence[Mapping[str, Union[str, Number, date, datetime]]],
    *,
    date_key: str = "occurred_at",
    amount_key: str = "amount",
) -> Dict[str, float]:
    """Aggregate purchases by YYYY-MM.

    Accepts `occurred_at` as date, datetime, or ISO string.
    """
    totals: Dict[str, float] = defaultdict(float)
    for row in purchases:
        dt = row.get(date_key)
        if isinstance(dt, str):
            try:
                parsed = datetime.fromisoformat(dt)
            except Exception:
                parsed = datetime.utcnow()
        elif isinstance(dt, datetime):
            parsed = dt
        elif isinstance(dt, date):
            parsed = datetime(dt.year, dt.month, dt.day)
        else:
            parsed = datetime.utcnow()
        key = month_key(parsed)
        totals[key] += to_float(row.get(amount_key))
    return {k: round(v, 2) for k, v in totals.items()}


# ---------------------------------------------------------------------------
# Streaks & no-spend days
# ---------------------------------------------------------------------------

def longest_no_spend_streak(purchase_dates: Iterable[date]) -> int:
    """Return the longest streak (in days) without purchases from a set of dates.

    Provide ALL calendar dates that had purchases; the function computes gaps.
    """
    days = sorted(set(purchase_dates))
    if not days:
        return 0
    # Build gaps between days
    longest = 0
    prev = days[0]
    for curr in days[1:]:
        gap = (curr - prev).days - 1  # days with no purchases between two purchase days
        if gap > longest:
            longest = gap
        prev = curr
    return max(longest, 0)


# ---------------------------------------------------------------------------
# Moving averages & smoothing
# ---------------------------------------------------------------------------

def moving_average(values: Sequence[Number], window: int = 3) -> List[float]:
    """Simple moving average; returns list of same length (head is partial)."""
    if window <= 0:
        raise ValueError("window must be > 0")
    out: List[float] = []
    acc = 0.0
    for i, v in enumerate(values):
        acc += to_float(v)
        start = max(0, i - window + 1)
        count = i - start + 1
        if start > 0:
            acc -= to_float(values[start - 1])
        out.append(round(acc / count, 4))
    return out


# ---------------------------------------------------------------------------
# Debt payoff (rough projection)
# ---------------------------------------------------------------------------

def payoff_projection(
    *,
    balance: Number,
    apr: Number,
    monthly_payment: Number,
    max_months: int = 600,
) -> Dict[str, float]:
    """Very rough amortization to forecast months to pay off and interest paid.

    Assumes interest compounds monthly at APR/12. Stops when balance <= 0 or max_months reached.
    Returns dict: {months, interest_paid, final_balance}.
    """
    b = to_float(balance)
    r = to_float(apr) / 12.0
    p = to_float(monthly_payment)

    months = 0
    interest_paid = 0.0
    # Avoid infinite loops when payment is too small
    if p <= b * r:
        return {"months": float("inf"), "interest_paid": float("inf"), "final_balance": b}

    while b > 0 and months < max_months:
        interest = b * r
        b = b + interest - p
        interest_paid += interest
        months += 1

    return {
        "months": float(months),
        "interest_paid": round(max(interest_paid, 0.0), 2),
        "final_balance": round(max(b, 0.0), 2),
    }


__all__ = [
    # helpers
    "to_float",
    "month_key",
    # allocations
    "normalize_rules",
    "allocate_budget",
    "compliance_report",
    # aggregations
    "aggregate_by_category",
    "aggregate_by_month",
    # streaks
    "longest_no_spend_streak",
    # smoothing
    "moving_average",
    # debt
    "payoff_projection",
]

