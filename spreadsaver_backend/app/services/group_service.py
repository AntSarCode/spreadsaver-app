from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

# Optional model imports (tolerate missing during early scaffolding)
try:  # pragma: no cover
    from app.models.models import Group, GroupMember, User  # type: ignore
except Exception:  # pragma: no cover
    Group = None  # type: ignore
    GroupMember = None  # type: ignore
    User = None  # type: ignore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_row(id: Any, name: str, role: Optional[str] = None):
    """Return a lightweight object with id/name/role attributes."""
    return SimpleNamespace(id=id, name=name, role=role)


def _ensure_models_available() -> bool:
    return all([Group is not None, GroupMember is not None])  # type: ignore


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_user_groups(db: Session, *, user_id: int) -> List[Any]:
    """Return a list of group-like rows with `.id`, `.name`, and optional `.role`.

    If models are not ready, returns an empty list.
    """
    if not _ensure_models_available():
        return []

    # Join membership → group to get role and name
    rows = (
        db.query(Group.id, Group.name, GroupMember.role)  # type: ignore[attr-defined]
        .join(GroupMember, GroupMember.group_id == Group.id)  # type: ignore[attr-defined]
        .filter(GroupMember.user_id == user_id)  # type: ignore[attr-defined]
        .order_by(Group.name.asc())
        .all()
    )
    return [_make_row(id=g_id, name=g_name, role=role) for (g_id, g_name, role) in rows]


def create_group(
    db: Session,
    *,
    owner_id: int,
    name: str,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a group and add the owner as admin member."""
    if not _ensure_models_available():
        return {"id": None, "name": name, "description": description, "owner_id": owner_id}

    # Name uniqueness per owner (soft rule)
    exists = (
        db.query(Group)  # type: ignore[attr-defined]
        .filter(and_(Group.owner_id == owner_id, func.lower(Group.name) == name.lower()))  # type: ignore[attr-defined]
        .first()
    )
    if exists:
        raise ValueError("Group with this name already exists for owner")

    grp = Group(owner_id=owner_id, name=name, description=description)  # type: ignore[call-arg]
    db.add(grp)
    db.flush()  # get grp.id

    member = GroupMember(group_id=grp.id, user_id=owner_id, role="owner")  # type: ignore[call-arg]
    db.add(member)
    db.commit()
    db.refresh(grp)

    return {"id": grp.id, "name": grp.name, "description": getattr(grp, "description", None)}


def add_member(
    db: Session,
    *,
    group_id: int,
    target_user_id: int,
    role: str = "member",
) -> Dict[str, Any]:
    """Add a user to a group with a role (default 'member')."""
    if not _ensure_models_available():
        return {"group_id": group_id, "user_id": target_user_id, "role": role}

    # Ensure group exists
    grp = db.query(Group).filter(Group.id == group_id).first()  # type: ignore[attr-defined]
    if not grp:
        raise ValueError("Group not found")

    existing = (
        db.query(GroupMember)  # type: ignore[attr-defined]
        .filter(and_(GroupMember.group_id == group_id, GroupMember.user_id == target_user_id))  # type: ignore[attr-defined]
        .first()
    )
    if existing:
        existing.role = role
    else:
        db.add(GroupMember(group_id=group_id, user_id=target_user_id, role=role))  # type: ignore[call-arg]

    db.commit()
    return {"group_id": group_id, "user_id": target_user_id, "role": role}


def remove_member(db: Session, *, group_id: int, target_user_id: int) -> bool:
    """Remove a user from a group. Returns True if deleted or not present."""
    if not _ensure_models_available():
        return True

    row = (
        db.query(GroupMember)  # type: ignore[attr-defined]
        .filter(and_(GroupMember.group_id == group_id, GroupMember.user_id == target_user_id))  # type: ignore[attr-defined]
        .first()
    )
    if not row:
        return True

    db.delete(row)
    db.commit()
    return True


def set_member_role(db: Session, *, group_id: int, target_user_id: int, role: str) -> Dict[str, Any]:
    """Update a member's role within a group."""
    if not _ensure_models_available():
        return {"group_id": group_id, "user_id": target_user_id, "role": role}

    row = (
        db.query(GroupMember)  # type: ignore[attr-defined]
        .filter(and_(GroupMember.group_id == group_id, GroupMember.user_id == target_user_id))  # type: ignore[attr-defined]
        .first()
    )
    if not row:
        raise ValueError("Membership not found")

    row.role = role
    db.commit()
    return {"group_id": group_id, "user_id": target_user_id, "role": role}


def list_group_members(db: Session, *, group_id: int) -> List[Dict[str, Any]]:
    """List members for a given group with their roles."""
    if not _ensure_models_available():
        return []

    q = db.query(GroupMember).filter(GroupMember.group_id == group_id)  # type: ignore[attr-defined]
    rows = q.all()
    return [
        {"user_id": r.user_id, "role": r.role}
        for r in rows
    ]


__all__ = [
    "list_user_groups",
    "create_group",
    "add_member",
    "remove_member",
    "set_member_role",
    "list_group_members",
]

