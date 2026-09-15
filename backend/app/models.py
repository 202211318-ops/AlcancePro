from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Document):
    name: str
    email: Indexed(str, unique=True)
    password_hash: str
    role: str = "ANALISTA"
    is_active: bool = True
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "users"


class Expediente(Document):
    code: Indexed(str, unique=True)
    name: str
    entity: str = ""
    sector: str = "MIXTO"
    contract_type: str = "PUBLICO"
    status: str = "BORRADOR"
    notes: str = ""
    owner_id: PydanticObjectId
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "expedientes"
        indexes = [
            IndexModel([("owner_id", 1), ("created_at", -1)]),
            IndexModel([("status", 1)]),
        ]


class ContractDocument(Document):
    expediente_id: PydanticObjectId
    doc_type: str
    original_name: str
    stored_name: str
    mime: str = ""
    size_bytes: int = 0
    extracted_text: str = ""
    extraction_status: str = "PENDING"
    uploaded_by: PydanticObjectId
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "documents"
        indexes = [IndexModel([("expediente_id", 1), ("created_at", -1)])]


class AnalysisJob(Document):
    expediente_id: PydanticObjectId
    status: str = "QUEUED"
    model: str = ""
    prompt_version: str = "v1"
    summary: dict = Field(default_factory=dict)
    error: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_by: PydanticObjectId
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "analysis_jobs"
        indexes = [IndexModel([("expediente_id", 1), ("created_at", -1)])]


class ScopeItem(Document):
    expediente_id: PydanticObjectId
    analysis_id: Optional[PydanticObjectId] = None
    scope_kind: str
    numeral: str
    hierarchy: str = ""
    bases: str = ""
    consultas: str = ""
    propuesta: str = ""
    contrato: str = ""
    compliance: str = "PENDIENTE"
    has_contradiction: bool = False
    sort_order: int = 0

    class Settings:
        name = "scope_items"
        indexes = [IndexModel([("expediente_id", 1), ("sort_order", 1)])]


class Deliverable(Document):
    expediente_id: PydanticObjectId
    analysis_id: Optional[PydanticObjectId] = None
    numeral: str
    name: str
    reference: str = ""
    due_term: str = ""
    compliance: str = "PENDIENTE"
    sort_order: int = 0

    class Settings:
        name = "deliverables"
        indexes = [IndexModel([("expediente_id", 1), ("sort_order", 1)])]


class AuditLog(Document):
    expediente_id: Optional[PydanticObjectId] = None
    user_id: Optional[PydanticObjectId] = None
    action: str
    detail: str = ""
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "audit_logs"


class AppSettings(Document):
    key: str = "global"
    llm_api_key: str = ""
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    llm_model: str = "gemini-flash-latest"

    class Settings:
        name = "app_settings"


DOCUMENT_MODELS = [
    User,
    Expediente,
    ContractDocument,
    AnalysisJob,
    ScopeItem,
    Deliverable,
    AuditLog,
    AppSettings,
]
