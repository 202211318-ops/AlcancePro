from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from beanie.operators import In

from ..access import can_mutate
from ..compliance import VALID_CODES, normalize_compliance
from ..deps import get_current_user, require_roles
from ..models import AnalysisJob, AuditLog, Deliverable, Expediente, ScopeItem, User
from ..schemas import DeliverableUpdateIn, ScopeItemUpdateIn, serialize_deliverable, serialize_job, serialize_scope
from ..services.excel import build_workbook
from ..services.llm import run_analysis

router = APIRouter(tags=["analysis"])


async def _get_expediente(expediente_id: str, user: User, mutate: bool = False) -> Expediente:
    item = await Expediente.get(expediente_id)
    if not item:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    if mutate and user.role == "REVISOR":
        raise HTTPException(status_code=403, detail="El revisor consulta y marca cumplimiento, no modifica el expediente")
    return item


@router.post("/expedientes/{expediente_id}/analyze")
async def analyze(
    expediente_id: str,
    background: BackgroundTasks,
    user: User = Depends(require_roles("ADMIN", "ANALISTA")),
):
    if not can_mutate(user):
        raise HTTPException(status_code=403, detail="El rol Revisor no ejecuta el análisis")
    expediente = await _get_expediente(expediente_id, user, mutate=True)
    running = await AnalysisJob.find(
        AnalysisJob.expediente_id == expediente.id,
        In(AnalysisJob.status, ["QUEUED", "RUNNING"]),
    ).first_or_none()
    if running:
        raise HTTPException(status_code=409, detail="Ya hay un análisis en curso para este expediente")
    job = AnalysisJob(
        expediente_id=expediente.id,
        status="QUEUED",
        model="pendiente",
        created_by=user.id,
    )
    await job.insert()
    await AuditLog(expediente_id=expediente.id, user_id=user.id, action="ANALYZE", detail=str(job.id)).insert()
    background.add_task(run_analysis, str(job.id))
    return {"success": True, "data": serialize_job(job)}


@router.get("/expedientes/{expediente_id}/analysis")
async def latest_analysis(expediente_id: str, user: User = Depends(get_current_user)):
    expediente = await _get_expediente(expediente_id, user)
    job = await AnalysisJob.find(AnalysisJob.expediente_id == expediente.id).sort("-created_at").first_or_none()
    return {"success": True, "data": serialize_job(job) if job else None}


@router.get("/expedientes/{expediente_id}/checklist")
async def checklist(expediente_id: str, user: User = Depends(get_current_user)):
    expediente = await _get_expediente(expediente_id, user)
    items = await ScopeItem.find(ScopeItem.expediente_id == expediente.id).sort("+sort_order").to_list()
    return {"success": True, "data": [serialize_scope(item) for item in items]}


@router.patch("/checklist/{item_id}")
async def update_checklist(item_id: str, payload: ScopeItemUpdateIn, user: User = Depends(get_current_user)):
    item = await ScopeItem.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Ítem no encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "compliance" in data:
        if data["compliance"] not in VALID_CODES:
            raise HTTPException(status_code=400, detail="Estado de seguimiento operativo no válido")
        data["compliance"] = normalize_compliance(data["compliance"])
    if user.role == "REVISOR":
        data = {"compliance": data["compliance"]} if "compliance" in data else {}
        if not data:
            raise HTTPException(status_code=403, detail="El revisor solo puede marcar seguimiento operativo")
    for key, value in data.items():
        setattr(item, key, value)
    item.has_contradiction = any(
        "REQUIERE ACLARACIÓN" in (getattr(item, field) or "")
        for field in ("bases", "consultas", "propuesta", "contrato")
    )
    await item.save()
    return {"success": True, "data": serialize_scope(item)}


@router.get("/expedientes/{expediente_id}/deliverables")
async def deliverables(expediente_id: str, user: User = Depends(get_current_user)):
    expediente = await _get_expediente(expediente_id, user)
    items = await Deliverable.find(Deliverable.expediente_id == expediente.id).sort("+sort_order").to_list()
    return {"success": True, "data": [serialize_deliverable(item) for item in items]}


@router.patch("/deliverables/{item_id}")
async def update_deliverable(item_id: str, payload: DeliverableUpdateIn, user: User = Depends(get_current_user)):
    item = await Deliverable.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Entregable no encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "compliance" in data:
        if data["compliance"] not in VALID_CODES:
            raise HTTPException(status_code=400, detail="Estado de seguimiento operativo no válido")
        data["compliance"] = normalize_compliance(data["compliance"])
    if user.role == "REVISOR":
        data = {"compliance": data["compliance"]} if "compliance" in data else {}
        if not data:
            raise HTTPException(status_code=403, detail="El revisor solo puede marcar seguimiento operativo")
    for key, value in data.items():
        setattr(item, key, value)
    await item.save()
    return {"success": True, "data": serialize_deliverable(item)}


@router.get("/expedientes/{expediente_id}/export")
async def export_excel(expediente_id: str, user: User = Depends(get_current_user)):
    expediente = await _get_expediente(expediente_id, user)
    count = await ScopeItem.find(ScopeItem.expediente_id == expediente.id).count()
    if count == 0:
        raise HTTPException(status_code=400, detail="Ejecute el análisis antes de exportar el Excel")
    content = await build_workbook(expediente)
    filename = "Checklist_Alcance_Proyecto.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/dashboard")
async def dashboard(user: User = Depends(get_current_user)):
    items = await Expediente.find_all().to_list()
    by_status = {}
    for item in items:
        by_status[item.status] = by_status.get(item.status, 0) + 1
    pending = 0
    flags = 0
    for item in items:
        pending += await ScopeItem.find(ScopeItem.expediente_id == item.id, ScopeItem.compliance == "PENDIENTE").count()
        flags += await ScopeItem.find(ScopeItem.expediente_id == item.id, ScopeItem.has_contradiction == True).count()
    from ..routers.system import resolve_llm
    key, _base, _model = await resolve_llm()
    return {
        "success": True,
        "data": {
            "expedientes": len(items),
            "by_status": by_status,
            "pending_items": pending,
            "contradictions": flags,
            "llm_configured": bool(key),
            "mongodb_db": "alcancepro",
            "engine": "gemini" if key else "local",
        },
    }
