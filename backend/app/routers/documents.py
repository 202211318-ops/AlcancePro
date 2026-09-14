from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..config import settings
from ..deps import get_current_user, require_roles
from ..models import AuditLog, ContractDocument, Expediente, User
from ..schemas import serialize_document
from ..services.extraction import ALLOWED_EXTENSIONS, MAX_FILE_BYTES, MAX_FILE_MB, extract_text

router = APIRouter(tags=["documents"])

DOC_TYPES = {"BASES", "CONSULTAS", "PROPUESTA", "CONTRATO", "ADENDA", "ANEXO", "OTRO"}


async def _get_owned_expediente(expediente_id: str, user: User, mutate: bool = False) -> Expediente:
    item = await Expediente.get(expediente_id)
    if not item:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    if mutate and user.role == "REVISOR":
        raise HTTPException(status_code=403, detail="El revisor no carga ni elimina documentos")
    return item


@router.get("/expedientes/{expediente_id}/documents")
async def list_documents(expediente_id: str, user: User = Depends(get_current_user)):
    expediente = await _get_owned_expediente(expediente_id, user)
    items = await ContractDocument.find(ContractDocument.expediente_id == expediente.id).sort("-created_at").to_list()
    return {"success": True, "data": [serialize_document(item) for item in items]}


async def _store_upload(expediente: Expediente, kind: str, file: UploadFile, user: User) -> ContractDocument:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"{file.filename}: formato no soportado. Use PDF, DOCX, TXT, MD o XLSX.")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail=f"{file.filename}: el archivo está vacío")
    if len(raw) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"{file.filename}: supera {MAX_FILE_MB} MB",
        )

    stored_name = f"{uuid4().hex}{suffix}"
    dest = settings.upload_path / stored_name
    dest.write_bytes(raw)

    text = ""
    status_extract = "OK"
    try:
        text = extract_text(dest)
        if not text.strip():
            status_extract = "EMPTY"
    except Exception as exc:
        status_extract = "ERROR"
        text = f"No se pudo extraer texto: {exc}"

    item = ContractDocument(
        expediente_id=expediente.id,
        doc_type=kind,
        original_name=file.filename or stored_name,
        stored_name=stored_name,
        mime=file.content_type or "",
        size_bytes=len(raw),
        extracted_text=text,
        extraction_status=status_extract,
        uploaded_by=user.id,
    )
    await item.insert()
    await AuditLog(
        expediente_id=expediente.id,
        user_id=user.id,
        action="UPLOAD_DOCUMENT",
        detail=f"{kind}:{item.original_name}",
    ).insert()
    return item


@router.post("/expedientes/{expediente_id}/documents")
async def upload_document(
    expediente_id: str,
    doc_type: str = Form(...),
    files: list[UploadFile] | None = File(None),
    file: UploadFile | None = File(None),
    user: User = Depends(require_roles("ADMIN", "ANALISTA")),
):
    expediente = await _get_owned_expediente(expediente_id, user, mutate=True)
    kind = doc_type.upper().strip()
    if kind not in DOC_TYPES:
        raise HTTPException(status_code=400, detail="Tipo documental no válido")

    uploads = [item for item in (files or []) if item is not None and item.filename]
    if file is not None and file.filename:
        uploads.append(file)
    if not uploads:
        raise HTTPException(status_code=400, detail="Seleccione al menos un archivo")

    saved = []
    errors = []
    for upload in uploads:
        try:
            saved.append(serialize_document(await _store_upload(expediente, kind, upload, user)))
        except HTTPException as exc:
            errors.append(str(exc.detail))
    if not saved:
        raise HTTPException(status_code=400, detail=" · ".join(errors) or "No se pudo cargar ningún archivo")
    payload = {"success": True, "data": saved if len(saved) > 1 else saved[0]}
    if errors:
        payload["message"] = "Algunos archivos no se cargaron: " + " · ".join(errors)
    return payload


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, user: User = Depends(require_roles("ADMIN", "ANALISTA"))):
    item = await ContractDocument.get(document_id)
    if not item:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    expediente = await Expediente.get(item.expediente_id)
    if user.role == "REVISOR":
        raise HTTPException(status_code=403, detail="El revisor no elimina documentos")
    path = settings.upload_path / item.stored_name
    if path.exists():
        path.unlink()
    await item.delete()
    return {"success": True}
