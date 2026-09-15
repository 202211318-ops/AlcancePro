from __future__ import annotations

PENDIENTE = "PENDIENTE"
CUMPLIDO = "CUMPLIDO"
INCUMPLIDO = "INCUMPLIDO"

VALID_CODES = {PENDIENTE, CUMPLIDO, INCUMPLIDO, "NO_CUMPLE"}

DISPLAY = {
    PENDIENTE: "☐ Pendiente",
    CUMPLIDO: "☑ Cumplido",
    INCUMPLIDO: "☒ Incumplido",
}

DROPDOWN = '"☐ Pendiente,☑ Cumplido,☒ Incumplido"'


def normalize_compliance(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return PENDIENTE
    if raw in DISPLAY.values():
        return next(code for code, label in DISPLAY.items() if label == raw)
    key = " ".join(raw.upper().replace("_", " ").replace("☒", "").replace("☑", "").replace("☐", "").split())
    mapping = {
        "PENDIENTE": PENDIENTE,
        "CUMPLIDO": CUMPLIDO,
        "INCUMPLIDO": INCUMPLIDO,
        "NO CUMPLE": INCUMPLIDO,
        "NOCUMPLE": INCUMPLIDO,
        "INCUMPLE": INCUMPLIDO,
    }
    return mapping.get(key, PENDIENTE)


def display_compliance(value: str | None) -> str:
    return DISPLAY[normalize_compliance(value)]
