from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from .compliance import normalize_compliance


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=80)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserUpdateIn(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=80)


class ExpedienteIn(BaseModel):
    name: str = Field(min_length=3, max_length=240)
    entity: str = ""
    sector: str = "MIXTO"
    contract_type: str = "PUBLICO"
    notes: str = ""


class ExpedienteUpdateIn(BaseModel):
    name: Optional[str] = None
    entity: Optional[str] = None
    sector: Optional[str] = None
    contract_type: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class ScopeItemUpdateIn(BaseModel):
    bases: Optional[str] = None
    consultas: Optional[str] = None
    propuesta: Optional[str] = None
    contrato: Optional[str] = None
    compliance: Optional[str] = None
    scope_kind: Optional[str] = None
    numeral: Optional[str] = None
    hierarchy: Optional[str] = None


class DeliverableUpdateIn(BaseModel):
    numeral: Optional[str] = None
    name: Optional[str] = None
    reference: Optional[str] = None
    due_term: Optional[str] = None
    compliance: Optional[str] = None


def serialize_user(user) -> dict:
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if isinstance(user.created_at, datetime) else user.created_at,
    }


def serialize_expediente(item) -> dict:
    return {
        "id": str(item.id),
        "code": item.code,
        "name": item.name,
        "entity": item.entity,
        "sector": item.sector,
        "contract_type": item.contract_type,
        "status": item.status,
        "notes": item.notes,
        "owner_id": str(item.owner_id),
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


def serialize_document(item) -> dict:
    return {
        "id": str(item.id),
        "expediente_id": str(item.expediente_id),
        "doc_type": item.doc_type,
        "original_name": item.original_name,
        "mime": item.mime,
        "size_bytes": item.size_bytes,
        "extraction_status": item.extraction_status,
        "text_preview": (item.extracted_text or "")[:400],
        "has_text": bool((item.extracted_text or "").strip()),
        "created_at": item.created_at.isoformat(),
    }


def serialize_job(item) -> dict:
    return {
        "id": str(item.id),
        "expediente_id": str(item.expediente_id),
        "status": item.status,
        "model": item.model,
        "prompt_version": item.prompt_version,
        "summary": item.summary,
        "error": item.error,
        "started_at": item.started_at.isoformat() if item.started_at else None,
        "finished_at": item.finished_at.isoformat() if item.finished_at else None,
        "created_at": item.created_at.isoformat(),
    }


def serialize_scope(item) -> dict:
    return {
        "id": str(item.id),
        "expediente_id": str(item.expediente_id),
        "scope_kind": item.scope_kind,
        "numeral": item.numeral,
        "hierarchy": item.hierarchy,
        "bases": item.bases,
        "consultas": item.consultas,
        "propuesta": item.propuesta,
        "contrato": item.contrato,
        "compliance": normalize_compliance(item.compliance),
        "has_contradiction": item.has_contradiction,
        "sort_order": item.sort_order,
    }


def serialize_deliverable(item) -> dict:
    return {
        "id": str(item.id),
        "expediente_id": str(item.expediente_id),
        "numeral": item.numeral,
        "name": item.name,
        "reference": item.reference,
        "due_term": item.due_term,
        "compliance": normalize_compliance(getattr(item, "compliance", None)),
        "sort_order": item.sort_order,
    }
