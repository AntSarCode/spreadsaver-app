# SpreadSaver – Service aggregation routes
# This router exposes thin HTTP endpoints that delegate to domain services under app/services.
# It is intentionally minimal and safe for initial wiring. Fill in service calls as they are implemented.

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.routes.auth import get_current_user  # reuse auth dependency
from app.schemas.schemas import (
    MessageResponse,
    BadgeAssignRequest,
)

# Optional imports of services (comment/uncomment as implementation lands)
try:
    from app.services import badge_service  # type: ignore
except Exception:  # pragma: no cover
    badge_service = None  # placeholder

try:
    from app.services import budget_service  # type: ignore
except Exception:  # pragma: no cover
    budget_service = None

try:
    from app.services import group_service  # type: ignore
except Exception:  # pragma: no cover
    group_service = None

try:
    from app.services import stripe_service  # type: ignore
except Exception:  # pragma: no cover
    stripe_service = None


router = APIRouter(prefix="/service", tags=["Service"])  # top-level service namespace


# ---------------------------------------------------------------------------
# Models (lightweight request/response bodies for this router)
# ---------------------------------------------------------------------------
class BudgetSummaryResponse(BaseModel):
    """High-level monthly summary for the dashboard."""
    month: str  # e.g., "2025-10"
    total_spent: float = 0.0
    total_income: Optional[float] = None
    by_category: Dict[str, float] = Field(default_factory=dict)


class CheckoutCreateRequest(BaseModel):
    price_id: str
    mode: str = Field(default="subscription", description="'subscription' or 'payment'")
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CheckoutSessionResponse(BaseModel):
    id: Optional[str] = None
    url: str


class GroupSummary(BaseModel):
    id: int
    name: str
    role: Optional[str] = None


# ---------------------------------------------------------------------------
# Health & meta
# ---------------------------------------------------------------------------
@router.get("/health", response_model=Dict[str, Any])
async def service_health() -> Dict[str, Any]:
    """Simple liveness probe for the service layer."""
    return {"status": "ok", "service": "spreadsaver", "time": datetime.utcnow().isoformat()}


# ---------------------------------------------------------------------------
# Badge service endpoints
# ---------------------------------------------------------------------------
@router.post("/badges/assign", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def assign_badge(
    payload: BadgeAssignRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Admin-only: assign a badge to a user by id.
    Connects to app.services.badge_service.assign_badge once implemented.
    """
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    if badge_service and hasattr(badge_service, "assign_badge"):
        try:
            badge_service.assign_badge(
                db=db,
                user_id=payload.user_id,
                badge_id=payload.badge_id,
                reason=payload.reason,
                source="api",
            )
        except Exception as e:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(status_code=501, detail="Badge service not implemented")

    return MessageResponse(message="Badge assigned")


@router.post("/badges/evaluate", response_model=MessageResponse)
async def evaluate_my_badges(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Evaluate and (if qualified) award badges for the authenticated user."""
    if badge_service and hasattr(badge_service, "evaluate_user_badges"):
        try:
            count = badge_service.evaluate_user_badges(db=db, user_id=current_user.id)
        except Exception as e:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(status_code=501, detail="Badge evaluation not implemented")

    return MessageResponse(message=f"Evaluated badges. New awards: {count}")


# ---------------------------------------------------------------------------
# Budget service endpoints
# ---------------------------------------------------------------------------
@router.get("/budget/summary", response_model=BudgetSummaryResponse)
async def get_budget_summary(
    month: str = Query(..., description="Target month in YYYY-MM format"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return the dashboard summary for a given month."""
    if budget_service and hasattr(budget_service, "get_month_summary"):
        try:
            summary = budget_service.get_month_summary(db=db, user_id=current_user.id, month=month)
        except Exception as e:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(e))
        # Expecting summary as dict-like. Coerce into schema shape.
        return BudgetSummaryResponse(
            month=summary.get("month", month),
            total_spent=float(summary.get("total_spent", 0.0)),
            total_income=summary.get("total_income"),
            by_category=summary.get("by_category", {}),
        )
    else:
        # Basic placeholder until service exists
        return BudgetSummaryResponse(month=month, total_spent=0.0, by_category={})


# ---------------------------------------------------------------------------
# Group service endpoints
# ---------------------------------------------------------------------------
@router.get("/groups/my", response_model=List[GroupSummary])
async def list_my_groups(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return groups for the current user."""
    if group_service and hasattr(group_service, "list_user_groups"):
        try:
            rows = group_service.list_user_groups(db=db, user_id=current_user.id)
        except Exception as e:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(e))
        return [GroupSummary(id=r.id, name=r.name, role=getattr(r, "role", None)) for r in rows]
    # Placeholder empty list until implemented
    return []


# ---------------------------------------------------------------------------
# Stripe service endpoints
# ---------------------------------------------------------------------------
@router.post("/stripe/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    body: CheckoutCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a Stripe Checkout Session for subscriptions or one-time payments."""
    if stripe_service and hasattr(stripe_service, "create_checkout_session"):
        try:
            session = stripe_service.create_checkout_session(
                user_id=current_user.id,
                price_id=body.price_id,
                mode=body.mode,
                success_url=body.success_url,
                cancel_url=body.cancel_url,
                metadata=body.metadata,
            )
            return CheckoutSessionResponse(id=getattr(session, "id", None), url=getattr(session, "url", ""))
        except Exception as e:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(status_code=501, detail="Stripe checkout not implemented")


@router.post("/stripe/webhook", status_code=200)
async def stripe_webhook(request: Request):
    """Receive Stripe webhook events. Public endpoint (no auth)."""
    if not stripe_service or not hasattr(stripe_service, "handle_webhook"):
        raise HTTPException(status_code=501, detail="Stripe webhook not implemented")

    signature = request.headers.get("stripe-signature") or request.headers.get("Stripe-Signature")
    payload = await request.body()

    try:
        stripe_service.handle_webhook(payload=payload, signature=signature)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=400, detail=str(e))

    return {"received": True}


__all__ = ["router"]
