from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..access import can_edit_settings
from ..config import settings
from ..deps import get_current_user
from ..models import AppSettings, DOCUMENT_MODELS, User

router = APIRouter(prefix="/system", tags=["system"])


class LlmSettingsIn(BaseModel):
    llm_api_key: str = ""
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    llm_model: str = "gemini-flash-latest"


async def get_app_settings() -> AppSettings:
    item = await AppSettings.find_one(AppSettings.key == "global")
    if not item:
        item = AppSettings(
            key="global",
            llm_api_key=settings.llm_api_key,
            llm_base_url=settings.llm_base_url,
            llm_model=settings.llm_model,
        )
        await item.insert()
    return item


async def resolve_llm() -> tuple[str, str, str]:
    stored = await get_app_settings()
    key = (stored.llm_api_key or settings.llm_api_key or "").strip()
    base = (stored.llm_base_url or settings.llm_base_url or "https://generativelanguage.googleapis.com/v1beta").strip()
    model_name = (stored.llm_model or settings.llm_model or "gemini-2.5-flash").strip()
    return key, base, model_name


def _mask(key: str) -> str:
    key = key.strip()
    if not key:
        return ""
    if len(key) <= 8:
        return "••••"
    return f"{key[:4]}…{key[-4:]}"


@router.get("/status")
async def system_status(user: User = Depends(get_current_user)):
    key, base, model_name = await resolve_llm()
    collections = []
    for doc_model in DOCUMENT_MODELS:
        collections.append({
            "name": doc_model.Settings.name,
            "count": await doc_model.find({}).count(),
        })
    return {
        "success": True,
        "data": {
            "mongodb": {
                "connected": True,
                "uri": "mongodb://127.0.0.1:27017",
                "database": settings.mongodb_db,
                "collections": collections,
            },
            "llm": {
                "configured": bool(key),
                "masked_key": _mask(key),
                "base_url": base,
                "model": model_name,
                "engine": "gemini" if key else "local",
            },
            "user": {"name": user.name, "email": user.email, "role": user.role},
        },
    }


@router.put("/llm")
async def save_llm(payload: LlmSettingsIn, user: User = Depends(get_current_user)):
    if not can_edit_settings(user):
        raise HTTPException(status_code=403, detail="Solo el administrador puede guardar la clave de IA")
    stored = await get_app_settings()
    if payload.llm_api_key.strip() and payload.llm_api_key.strip() != stored.llm_api_key:
        stored.llm_api_key = payload.llm_api_key.strip()
    stored.llm_base_url = payload.llm_base_url.strip() or stored.llm_base_url
    stored.llm_model = payload.llm_model.strip() or stored.llm_model
    await stored.save()
    key, base, model_name = await resolve_llm()
    return {
        "success": True,
        "data": {"configured": bool(key), "masked_key": _mask(key), "base_url": base, "model": model_name},
    }
