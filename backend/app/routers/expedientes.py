from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from ..config import settings
from ..deps import get_current_user, require_roles
from ..models import AnalysisJob, AuditLog, ContractDocument, Deliverable, Expediente, ScopeItem, User
from ..schemas import ExpedienteIn, ExpedienteUpdateIn, serialize_expediente

router = APIRouter(prefix="/expedientes", tags=["expedientes"])


async def next_code() -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"EXP-{year}-"
    last = await Expediente.find({"code": {"$regex": f"^{prefix}"}}).sort("-code").first_or_none()
    sequence = 1
    if last and last.code[len(prefix):].isdigit():
        sequence = int(last.code[len(prefix):]) + 1
    return f"{prefix}{sequence:04d}"


@router.get("")
async def list_expedientes(user: User = Depends(get_current_user)):
    items = await Expediente.find_all().sort("-updated_at").to_list()
    return {"success": True, "data": [serialize_expediente(item) for item in items]}


@router.post("")
async def create_expediente(payload: ExpedienteIn, user: User = Depends(require_roles("ADMIN", "ANALISTA"))):
    if payload.sector not in {"TI", "OBRAS", "CONSULTORIA", "SERVICIOS", "MIXTO"}:
        raise HTTPException(status_code=400, detail="Sector no válido")
    if payload.contract_type not in {"PUBLICO", "PRIVADO"}:
        raise HTTPException(status_code=400, detail="Tipo de contratación no válido")
    item = Expediente(
        code=await next_code(),
        name=payload.name.strip(),
        entity=payload.entity.strip(),
        sector=payload.sector,
        contract_type=payload.contract_type,
        notes=payload.notes.strip(),
        owner_id=user.id,
        status="BORRADOR",
    )
    await item.insert()
    await AuditLog(expediente_id=item.id, user_id=user.id, action="CREATE_EXPEDIENTE", detail=item.code).insert()
    return {"success": True, "data": serialize_expediente(item)}


@router.get("/{expediente_id}")
async def get_expediente(expediente_id: str, user: User = Depends(get_current_user)):
    item = await Expediente.get(expediente_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expediente no encontrado")
    docs = await ContractDocument.find(ContractDocument.expediente_id == item.id).to_list()
    jobs = await AnalysisJob.find(AnalysisJob.expediente_id == item.id).sort("-created_at").to_list()
    scope_count = await ScopeItem.find(ScopeItem.expediente_id == item.id).count()
    deliv_count = await Deliverable.find(Deliverable.expediente_id == item.id).count()
    pending = await ScopeItem.find(ScopeItem.expediente_id == item.id, ScopeItem.compliance == "PENDIENTE").count()
    flags = await ScopeItem.find(ScopeItem.expediente_id == item.id, ScopeItem.has_contradiction == True).count()
    return {
        "success": True,
        "data": {
            **serialize_expediente(item),
            "stats": {
                "documents": len(docs),
                "checklist": scope_count,
                "deliverables": deliv_count,
                "pending": pending,
                "contradictions": flags,
            },
            "latest_job": {
                "id": str(jobs[0].id),
                "status": jobs[0].status,
                "error": jobs[0].error,
                "summary": jobs[0].summary,
            } if jobs else None,
        },
    }


@router.patch("/{expediente_id}")
async def update_expediente(
    expediente_id: str,
    payload: ExpedienteUpdateIn,
    user: User = Depends(require_roles("ADMIN", "ANALISTA")),
):
    item = await Expediente.get(expediente_id)
    if not item:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value.strip() if isinstance(value, str) else value)
    item.updated_at = datetime.now(timezone.utc)
    await item.save()
    return {"success": True, "data": serialize_expediente(item)}


@router.delete("/{expediente_id}")
async def delete_expediente(expediente_id: str, user: User = Depends(require_roles("ADMIN", "ANALISTA"))):
    item = await Expediente.get(expediente_id)
    if not item:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    documents = await ContractDocument.find(ContractDocument.expediente_id == item.id).to_list()
    for document in documents:
        path = settings.upload_path / document.stored_name
        if path.exists():
            path.unlink()
    await ContractDocument.find(ContractDocument.expediente_id == item.id).delete()
    await AnalysisJob.find(AnalysisJob.expediente_id == item.id).delete()
    await ScopeItem.find(ScopeItem.expediente_id == item.id).delete()
    await Deliverable.find(Deliverable.expediente_id == item.id).delete()
    await AuditLog(expediente_id=item.id, user_id=user.id, action="DELETE_EXPEDIENTE", detail=item.code).insert()
    await item.delete()
    return {"success": True}
