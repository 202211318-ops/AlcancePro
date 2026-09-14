from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import require_roles
from ..models import User
from ..schemas import UserUpdateIn, serialize_user
from ..security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
async def list_users(_admin: User = Depends(require_roles("ADMIN"))):
    users = await User.find_all().sort("+created_at").to_list()
    return {"success": True, "data": [serialize_user(item) for item in users]}


@router.patch("/{user_id}")
async def update_user(user_id: str, payload: UserUpdateIn, _admin: User = Depends(require_roles("ADMIN"))):
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "role" in data and data["role"] not in {"ADMIN", "ANALISTA", "REVISOR"}:
        raise HTTPException(status_code=400, detail="Rol no válido")
    if data.get("password"):
        user.password_hash = hash_password(data.pop("password"))
    for key, value in data.items():
        setattr(user, key, value)
    await user.save()
    return {"success": True, "data": serialize_user(user)}
