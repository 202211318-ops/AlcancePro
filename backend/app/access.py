from fastapi import HTTPException

from .models import Expediente, User

ROLES = ("ADMIN", "ANALISTA", "REVISOR")


def can_manage_users(user: User) -> bool:
    return user.role == "ADMIN"


def can_edit_settings(user: User) -> bool:
    return user.role == "ADMIN"


def can_mutate(user: User) -> bool:
    return user.role in {"ADMIN", "ANALISTA"}


def assert_can_mutate(user: User) -> None:
    if not can_mutate(user):
        raise HTTPException(status_code=403, detail="El rol Revisor solo consulta y marca cumplimiento")


def assert_can_access(_user: User, _item: Expediente | None = None) -> None:
    return None
