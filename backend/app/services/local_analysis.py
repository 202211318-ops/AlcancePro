from __future__ import annotations

import re

HEADING_RE = re.compile(
    r"^\s*(?:(?:artículo|articulo|cláusula|clausula|numeral|ítem|item|sección|seccion)\s+)?"
    r"(\d+(?:\.\d+){0,6})(?:[\.\)\-:])\s+(.+)$",
    re.IGNORECASE,
)
PLAZO_RE = re.compile(r"(\d+\s+días?\s+(?:calendario|hábiles|habiles)?|\d+\s+meses?)", re.IGNORECASE)
PROJECT_WORDS = (
    "reunión", "reunion", "acta de", "plan del proyecto", "plan de trabajo",
    "informe mensual", "informe periódico", "informe periodico", "capacitación",
    "capacitacion", "cronograma", "coordinación", "coordinacion", "manual de usuario",
    "pruebas de", "protocolo de pruebas", "contingencia", "mesa de ayuda",
    "supervisor", "residente", "kick off", "puesta en marcha",
)
DELIVERABLE_WORDS = (
    "acta de inicio", "acta de culminación", "acta de culminacion", "acta de conformidad",
    "plan del proyecto", "plan de trabajo", "informe mensual", "informe de avance",
    "manual de usuario", "manual técnico", "manual tecnico", "certificado",
    "memoria descriptiva", "protocolo de pruebas", "evidencia", "cronograma",
)
SKIP_WORDS = (
    "declaración jurada", "declaracion jurada", "sobre n°", "sobre n",
    "garantía de seriedad", "garantia de seriedad", "propuesta económica sellada",
)


def _is_project(text: str) -> bool:
    lower = text.lower()
    return any(word in lower for word in PROJECT_WORDS)


def _is_skipped(text: str) -> bool:
    lower = text.lower()
    return any(word in lower for word in SKIP_WORDS)


def _num_key(numeral: str) -> tuple:
    parts = []
    for chunk in re.split(r"\D+", numeral):
        if chunk.isdigit():
            parts.append(int(chunk))
    return tuple(parts) or (9999,)


def extract_items(text: str) -> list[dict]:
    items = []
    current = None
    for raw in (text or "").splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line:
            if current and len(current["texto"]) > 800:
                items.append(current)
                current = None
            continue
        match = HEADING_RE.match(line)
        if match:
            if current:
                items.append(current)
            current = {"numeral": match.group(1), "texto": match.group(2).strip()}
            continue
        if current:
            current["texto"] = f"{current['texto']} {line}".strip()
    if current:
        items.append(current)
    if items:
        return [item for item in items if item["texto"] and not _is_skipped(item["texto"])]

    paragraphs = [re.sub(r"\s+", " ", block).strip() for block in re.split(r"\n\s*\n", text or "")]
    fallback = []
    for index, paragraph in enumerate(paragraphs, start=1):
        if len(paragraph) < 40 or _is_skipped(paragraph):
            continue
        fallback.append({"numeral": f"P-{index}", "texto": paragraph[:900]})
        if len(fallback) >= 80:
            break
    return fallback


def _column_for(doc_type: str) -> str:
    mapping = {
        "BASES": "bases",
        "ANEXO": "bases",
        "CONSULTAS": "consultas",
        "PROPUESTA": "propuesta",
        "CONTRATO": "contrato",
        "ADENDA": "contrato",
        "OTRO": "bases",
    }
    return mapping.get(doc_type, "bases")


def analyze_documents(documents: list) -> dict:
    merged: dict[str, dict] = {}
    deliverables = []

    for doc in documents:
        column = _column_for(getattr(doc, "doc_type", "OTRO"))
        filename = getattr(doc, "original_name", "")
        for item in extract_items(getattr(doc, "extracted_text", "") or ""):
            numeral = item["numeral"]
            row = merged.setdefault(
                numeral,
                {
                    "numeral": numeral,
                    "jerarquia": numeral,
                    "tipo_alcance": "PROYECTO" if _is_project(item["texto"]) else "PRODUCTO",
                    "bases": "",
                    "consultas": "",
                    "propuesta": "",
                    "contrato": "",
                },
            )
            previous = row[column]
            addition = item["texto"]
            row[column] = f"{previous} | {addition}".strip(" |") if previous and previous != addition else addition
            if _is_project(item["texto"]):
                row["tipo_alcance"] = "PROYECTO"
            lower = item["texto"].lower()
            if any(word in lower for word in DELIVERABLE_WORDS):
                plazo = ""
                found = PLAZO_RE.search(item["texto"])
                if found:
                    plazo = found.group(1)
                deliverables.append(
                    {
                        "numeral": numeral,
                        "entregable": item["texto"][:220],
                        "referencia_documental": f"{getattr(doc, 'doc_type', '')} / {filename}",
                        "plazo_entrega": plazo,
                    }
                )

    checklist = sorted(merged.values(), key=lambda row: _num_key(row["numeral"]))
    unique_deliverables = []
    seen = set()
    for item in deliverables:
        stamp = (item["numeral"], item["entregable"][:80])
        if stamp in seen:
            continue
        seen.add(stamp)
        unique_deliverables.append(item)

    return {
        "expediente": {
            "entidad_detectada": "",
            "objeto": "Extracción local por numerales del expediente",
            "sector": "MIXTO",
            "plazo_contractual": "",
            "observaciones": "Análisis local. Puede mejorar la calidad pegando una clave de Gemini en Configuración.",
        },
        "checklist": checklist,
        "entregables": unique_deliverables,
    }
