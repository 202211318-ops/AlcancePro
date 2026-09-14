from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import get_current_user
from ..models import User
from ..schemas import LoginIn, RegisterIn, serialize_user
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(payload: RegisterIn):
    existing = await User.find_one(User.email == payload.email.lower())
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El correo ya está registrado")
    user = User(
        name=payload.name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role="ANALISTA",
        is_active=True,
    )
    await user.insert()
    token = create_token(str(user.id), user.role)
    return {"success": True, "data": {"token": token, "user": serialize_user(user)}}


@router.post("/login")
async def login(payload: LoginIn):
    user = await User.find_one(User.email == payload.email.lower())
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")
    token = create_token(str(user.id), user.role)
    return {"success": True, "data": {"token": token, "user": serialize_user(user)}}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"success": True, "data": serialize_user(user)}
