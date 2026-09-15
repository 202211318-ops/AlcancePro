from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import httpx

from ..compliance import normalize_compliance
from ..models import AnalysisJob, Deliverable, Expediente, ScopeItem, utcnow
from ..prompt import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt


CONTRADICTION_MARK = "REQUIERE ACLARACIÓN"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        text = fenced.group(1).strip()
    return json.loads(text)


async def call_llm(user_prompt: str, api_key: str, base_url: str, model: str) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    url = base_url.rstrip("/") + "/chat/completions"
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code >= 400:
            raise RuntimeError(f"Error del modelo de IA ({response.status_code}): {response.text[:500]}")
        data = response.json()
    content = data["choices"][0]["message"]["content"]
    try:
        parsed = _parse_json(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"El modelo no devolvió JSON válido: {exc}") from exc
    if not isinstance(parsed, dict) or "checklist" not in parsed:
        raise RuntimeError("La respuesta del modelo no contiene la matriz de alcance.")
    return parsed


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[TEXTO TRUNCADO POR LÍMITE DE CONTEXTO]"


def _row_has_contradiction(item: dict) -> bool:
    fields = [item.get("bases") or "", item.get("consultas") or "", item.get("propuesta") or "", item.get("contrato") or ""]
    return any(CONTRADICTION_MARK in value for value in fields)


async def persist_analysis(expediente: Expediente, job: AnalysisJob, result: dict) -> None:
    await ScopeItem.find(ScopeItem.expediente_id == expediente.id).delete()
    await Deliverable.find(Deliverable.expediente_id == expediente.id).delete()

    checklist = result.get("checklist") or []
    entregables = result.get("entregables") or []
    contradictions = 0

    for index, item in enumerate(checklist):
        kind = str(item.get("tipo_alcance") or "PROYECTO").upper()
        if kind not in {"PRODUCTO", "PROYECTO"}:
            kind = "PROYECTO"
        has_flag = _row_has_contradiction(item)
        contradictions += int(has_flag)
        row = ScopeItem(
            expediente_id=expediente.id,
            analysis_id=job.id,
            scope_kind=kind,
            numeral=str(item.get("numeral") or "").strip() or f"S/N-{index + 1}",
            hierarchy=str(item.get("jerarquia") or "").strip(),
            bases=str(item.get("bases") or "").strip(),
            consultas=str(item.get("consultas") or "").strip(),
            propuesta=str(item.get("propuesta") or "").strip(),
            contrato=str(item.get("contrato") or "").strip(),
            compliance=normalize_compliance(item.get("seguimiento_operativo") or item.get("compliance")),
            has_contradiction=has_flag,
            sort_order=index,
        )
        await row.insert()

    for index, item in enumerate(entregables):
        row = Deliverable(
            expediente_id=expediente.id,
            analysis_id=job.id,
            numeral=str(item.get("numeral") or "").strip(),
            name=str(item.get("entregable") or "").strip(),
            reference=str(item.get("referencia_documental") or "").strip(),
            due_term=str(item.get("plazo_entrega") or "").strip(),
            compliance=normalize_compliance(item.get("seguimiento_operativo") or item.get("compliance")),
            sort_order=index,
        )
        if row.name:
            await row.insert()

    meta = result.get("expediente") or {}
    if meta.get("entidad_detectada") and not expediente.entity:
        expediente.entity = str(meta["entidad_detectada"])[:240]
    if meta.get("sector") in {"TI", "OBRAS", "CONSULTORIA", "SERVICIOS", "MIXTO"}:
        expediente.sector = meta["sector"]

    job.status = "COMPLETED"
    job.finished_at = utcnow()
    job.summary = {
        "objeto": meta.get("objeto") or "",
        "plazo_contractual": meta.get("plazo_contractual") or "",
        "observaciones": meta.get("observaciones") or "",
        "filas_checklist": len(checklist),
        "filas_entregables": len(entregables),
        "contradicciones": contradictions,
        "producto": sum(1 for item in checklist if str(item.get("tipo_alcance") or "").upper() == "PRODUCTO"),
        "proyecto": sum(1 for item in checklist if str(item.get("tipo_alcance") or "").upper() != "PRODUCTO"),
    }
    await job.save()

    expediente.status = "LISTO"
    expediente.updated_at = utcnow()
    await expediente.save()


async def run_analysis(job_id: str) -> None:
    job = await AnalysisJob.get(job_id)
    if not job:
        return
    expediente = await Expediente.get(job.expediente_id)
    if not expediente:
        job.status = "FAILED"
        job.error = "Expediente no encontrado"
        job.finished_at = utcnow()
        await job.save()
        return

    from ..models import ContractDocument
    from ..routers.system import resolve_llm
    from .gemini import analyze_with_gemini

    api_key, _base, model = await resolve_llm()
    job.status = "RUNNING"
    job.started_at = utcnow()
    job.model = model if api_key else "extractor-local"
    job.prompt_version = PROMPT_VERSION
    await job.save()

    expediente.status = "EN_ANALISIS"
    expediente.updated_at = utcnow()
    await expediente.save()

    try:
        documents = await ContractDocument.find(ContractDocument.expediente_id == expediente.id).to_list()
        if not documents:
            raise RuntimeError("Cargue al menos un documento antes de analizar.")
        if not api_key:
            from .local_analysis import analyze_documents
            usable = [doc for doc in documents if (doc.extracted_text or "").strip()]
            if not usable:
                raise RuntimeError("No hay texto extraíble y no hay clave de Gemini configurada.")
            result = analyze_documents(usable)
        else:
            result, used_model = await analyze_with_gemini(documents, api_key, model)
            job.model = used_model
        await persist_analysis(expediente, job, result)
    except Exception as exc:
        job.status = "FAILED"
        job.error = str(exc)
        job.finished_at = utcnow()
        await job.save()
        expediente.status = "BORRADOR"
        expediente.updated_at = utcnow()
        await expediente.save()
