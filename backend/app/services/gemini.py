from __future__ import annotations

import asyncio
import base64
import json
import re
from pathlib import Path

import httpx

from ..config import settings
from ..prompt import SYSTEM_PROMPT

GEMINI_MODELS = [
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
]

INLINE_PDF_MAX = 4 * 1024 * 1024
TEXT_CHARS = 90000
FILES_API = "https://generativelanguage.googleapis.com/upload/v1beta/files"
GENERATE_API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

TRANSIENT_MARKERS = (
    "503",
    "429",
    "unavailable",
    "high demand",
    "try again",
    "overloaded",
    "resource_exhausted",
    "timeout",
    "temporar",
    "agotado",
    "404",
    "not found",
)


def _parse_json(raw: str) -> dict:
    text = (raw or "").strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        text = fenced.group(1).strip()
    return json.loads(text)


def _text_from_response(data: dict) -> str:
    if data.get("error"):
        raise RuntimeError(str(data["error"].get("message") or data["error"]))
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini no devolvió resultados. Revise la clave o el modelo.")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    return "".join(
        part.get("text") or ""
        for part in parts
        if not part.get("thought")
    ).strip()


def _safe_error(status: int, body: str) -> str:
    cleaned = re.sub(r"AQ\.[A-Za-z0-9_-]+", "AQ.***", body or "")
    cleaned = re.sub(r"AIza[0-9A-Za-z_-]+", "AIza***", cleaned)
    lowered = cleaned.lower()
    if status in {429, 503} or "high demand" in lowered or "unavailable" in lowered:
        return f"Gemini ({status}): saturado temporalmente"
    return f"Gemini ({status}): {cleaned[:400]}"


def _is_transient(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in TRANSIENT_MARKERS)


async def _wait_active(client: httpx.AsyncClient, api_key: str, file_name: str) -> str:
    headers = {"x-goog-api-key": api_key}
    name = file_name if file_name.startswith("files/") else f"files/{file_name}"
    url = f"https://generativelanguage.googleapis.com/v1beta/{name}"
    for _ in range(15):
        response = await client.get(url, headers=headers)
        if response.status_code >= 400:
            break
        data = response.json()
        if (data.get("state") or "").upper() == "ACTIVE":
            return data.get("uri") or f"https://generativelanguage.googleapis.com/v1beta/{name}"
        await asyncio.sleep(0.35)
    return f"https://generativelanguage.googleapis.com/v1beta/{name}"


async def _upload_pdf(client: httpx.AsyncClient, api_key: str, path: Path, display_name: str) -> str:
    raw = path.read_bytes()
    start = await client.post(
        FILES_API,
        headers={
            "x-goog-api-key": api_key,
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(len(raw)),
            "X-Goog-Upload-Header-Content-Type": "application/pdf",
            "Content-Type": "application/json",
        },
        json={"file": {"display_name": display_name[:120]}},
    )
    if start.status_code >= 400:
        raise RuntimeError(_safe_error(start.status_code, start.text))
    upload_url = start.headers.get("x-goog-upload-url") or start.headers.get("X-Goog-Upload-URL")
    if not upload_url:
        raise RuntimeError("Gemini no devolvió URL de carga de PDF.")
    finish = await client.post(
        upload_url,
        headers={
            "x-goog-api-key": api_key,
            "Content-Length": str(len(raw)),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        },
        content=raw,
    )
    if finish.status_code >= 400:
        raise RuntimeError(_safe_error(finish.status_code, finish.text))
    info = (finish.json() or {}).get("file") or {}
    file_name = info.get("name") or ""
    uri = info.get("uri") or ""
    if file_name and (info.get("state") or "").upper() != "ACTIVE":
        uri = await _wait_active(client, api_key, file_name) or uri
    if not uri:
        raise RuntimeError("Gemini no devolvió la referencia del PDF subido.")
    return uri


async def _build_parts(documents: list, api_key: str) -> tuple[list[dict], bool]:
    parts: list[dict] = [
        {
            "text": SYSTEM_PROMPT
            + "\n\nAnaliza TODOS los documentos completos. Extrae el 100% de requisitos, plazos y entregables. "
            "Usa la clasificación de cada archivo. No detengas el análisis en una muestra. "
            "Seguimiento operativo: PENDIENTE por defecto; CUMPLIDO solo con evidencia de ejecución; "
            "INCUMPLIDO solo con evidencia de retraso o rechazo. Responde solo JSON."
        }
    ]
    attached = 0
    used_files_api = False
    async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=20.0)) as client:
        for doc in documents:
            label = f"===== DOCUMENTO CLASIFICADO COMO: {doc.doc_type} | ARCHIVO: {doc.original_name} ====="
            path = settings.upload_path / doc.stored_name
            suffix = Path(doc.original_name or doc.stored_name).suffix.lower()
            text = (doc.extracted_text or "").strip()
            if text:
                parts.append({"text": f"{label}\n{text[:TEXT_CHARS]}"})
                attached += 1
                continue
            if suffix != ".pdf" or not path.exists() or path.stat().st_size <= 0:
                continue
            size = path.stat().st_size
            parts.append({"text": label})
            if size <= INLINE_PDF_MAX:
                parts.append(
                    {
                        "inline_data": {
                            "mime_type": "application/pdf",
                            "data": base64.standard_b64encode(path.read_bytes()).decode("ascii"),
                        }
                    }
                )
            else:
                uri = await _upload_pdf(client, api_key, path, doc.original_name or path.name)
                parts.append({"file_data": {"mime_type": "application/pdf", "file_uri": uri}})
                used_files_api = True
            attached += 1
    if attached == 0:
        raise RuntimeError("No hay PDF ni texto extraíble para enviar a Gemini.")
    return parts, used_files_api


async def _generate(api_key: str, model: str, parts: list[dict], timeout: float) -> dict:
    url = GENERATE_API.format(model=model)
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "maxOutputTokens": 32768,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    response = None
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=20.0)) as client:
        for attempt in range(2):
            try:
                response = await client.post(url, headers=headers, json=payload)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt >= 1:
                    raise RuntimeError(f"Gemini ({model}): tiempo de espera agotado") from exc
                await asyncio.sleep(1)
                continue
            if response.status_code >= 400 and "thinking" in (response.text or "").lower():
                payload["generationConfig"].pop("thinkingConfig", None)
                response = await client.post(url, headers=headers, json=payload)
            if response.status_code in {429, 503} and attempt == 0:
                await asyncio.sleep(1)
                continue
            break
    if response is None:
        raise RuntimeError(f"Gemini ({model}): sin respuesta")
    if response.status_code >= 400:
        raise RuntimeError(_safe_error(response.status_code, response.text))
    data = response.json()
    finish = ((data.get("candidates") or [{}])[0].get("finishReason") or "").upper()
    content = _text_from_response(data)
    if not content:
        raise RuntimeError("Gemini devolvió una respuesta vacía.")
    if finish == "MAX_TOKENS":
        raise RuntimeError("Gemini cortó la respuesta por límite de tokens. Reduzca el número de PDF.")
    parsed = _parse_json(content)
    if not isinstance(parsed, dict) or "checklist" not in parsed:
        raise RuntimeError("Gemini no devolvió la matriz de alcance en JSON.")
    return parsed


async def analyze_with_gemini(documents: list, api_key: str, preferred_model: str) -> tuple[dict, str]:
    parts, used_files_api = await _build_parts(documents, api_key)
    timeout = 150.0 if used_files_api or any("inline_data" in part for part in parts) else 75.0
    tried: list[str] = []
    last_error = None
    models = [preferred_model] + [item for item in GEMINI_MODELS if item != preferred_model]
    for model in models[:3]:
        if not model or model in tried:
            continue
        tried.append(model)
        try:
            result = await _generate(api_key, model, parts, timeout)
            return result, model
        except json.JSONDecodeError as exc:
            last_error = RuntimeError(f"JSON inválido de {model}: {exc}")
        except Exception as exc:
            last_error = exc
            if not _is_transient(exc):
                break
    if last_error and _is_transient(last_error):
        raise RuntimeError(
            "Gemini está saturado en este momento. Pulse Ejecutar análisis otra vez en unos segundos."
        )
    raise RuntimeError(str(last_error) if last_error else "No se pudo contactar Gemini.")
