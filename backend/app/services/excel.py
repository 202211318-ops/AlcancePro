from io import BytesIO

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule
from openpyxl.worksheet.table import Table, TableStyleInfo

from ..models import Deliverable, Expediente, ScopeItem


NAVY = "0C1B2E"
GOLD = "B8943F"
TEAL = "1F6F66"
PARCHMENT = "F6F1E7"
WHITE = "FFFFFF"
RED = "8C2F2F"
GREEN = "1F6F3A"
AMBER = "8A6A1F"


def _fill(color: str) -> PatternFill:
    return PatternFill("solid", fgColor=color)


def _font(bold=False, color=WHITE, size=11, name="Calibri"):
    return Font(name=name, bold=bold, color=color, size=size)


def _border() -> Border:
    thin = Side(style="thin", color="C9C1B2")
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def _header(ws, row: int, values: list[str], fill: str) -> None:
    for col, value in enumerate(values, start=1):
        cell = ws.cell(row=row, column=col, value=value)
        cell.fill = _fill(fill)
        cell.font = _font(bold=True, color=WHITE, size=11)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = _border()


async def build_workbook(expediente: Expediente) -> bytes:
    items = await ScopeItem.find(ScopeItem.expediente_id == expediente.id).sort("+sort_order").to_list()
    deliverables = await Deliverable.find(Deliverable.expediente_id == expediente.id).sort("+sort_order").to_list()
    compliance_map = {"PENDIENTE": "Pendiente", "CUMPLIDO": "Cumplido", "NO_CUMPLE": "No Cumple"}
    checklist_df = pd.DataFrame(
        [
            {
                "scope_kind": item.scope_kind,
                "has_contradiction": item.has_contradiction,
                "Numeral del ítem": item.numeral,
                "Bases integradas / TDR / ET": item.bases,
                "Consultas": item.consultas,
                "Propuesta": item.propuesta,
                "Contrato": item.contrato,
                "Cumplimiento": compliance_map.get(item.compliance, "Pendiente"),
            }
            for item in items
        ]
    )
    deliverables_df = pd.DataFrame(
        [
            {
                "Numeral": item.numeral,
                "Entregable identificado": item.name,
                "Referencia documental": item.reference,
                "Plazo de entrega": item.due_term,
            }
            for item in deliverables
        ]
    )
    if not checklist_df.empty:
        checklist_df = checklist_df.fillna("")
    if not deliverables_df.empty:
        deliverables_df = deliverables_df.fillna("")

    wb = Workbook()
    ws = wb.active
    ws.title = "Checklist_Alcance"

    ws.merge_cells("A1:F1")
    title = ws["A1"]
    title.value = f"Matriz de Alcance Contractual — {expediente.code} — {expediente.name}"
    title.font = _font(bold=True, color=WHITE, size=14)
    title.fill = _fill(NAVY)
    title.alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells("A2:F2")
    subtitle = ws["A2"]
    subtitle.value = (
        f"Entidad: {expediente.entity or 'No identificada'}  |  "
        f"Sector: {expediente.sector}  |  Tipo: {expediente.contract_type}  |  Estado: {expediente.status}"
    )
    subtitle.font = _font(bold=False, color=NAVY, size=10)
    subtitle.fill = _fill(PARCHMENT)
    subtitle.alignment = Alignment(vertical="center")

    headers = [
        "Numeral del ítem",
        "Bases integradas / TDR / ET",
        "Consultas",
        "Propuesta",
        "Contrato",
        "Cumplimiento",
    ]
    _header(ws, 4, headers, TEAL)
    ws.row_dimensions[1].height = 28
    ws.row_dimensions[4].height = 22
    ws.freeze_panes = "A5"

    current_kind = None
    excel_row = 5
    for record in checklist_df.to_dict("records"):
        if record["scope_kind"] != current_kind:
            current_kind = record["scope_kind"]
            label = "ALCANCE DEL PRODUCTO" if current_kind == "PRODUCTO" else "ALCANCE DEL PROYECTO (GESTIÓN)"
            ws.merge_cells(start_row=excel_row, start_column=1, end_row=excel_row, end_column=6)
            cell = ws.cell(row=excel_row, column=1, value=label)
            cell.fill = _fill(GOLD)
            cell.font = _font(bold=True, color=NAVY, size=11)
            cell.alignment = Alignment(vertical="center")
            excel_row += 1
        values = [
            record["Numeral del ítem"],
            record["Bases integradas / TDR / ET"],
            record["Consultas"],
            record["Propuesta"],
            record["Contrato"],
            record["Cumplimiento"],
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=excel_row, column=col, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = _border()
            cell.font = Font(name="Calibri", size=10, color=NAVY)
            if col == 1:
                cell.font = Font(name="Calibri", size=10, bold=True, color=NAVY)
            if record["has_contradiction"]:
                cell.fill = PatternFill("solid", fgColor="F7E4C8")
        excel_row += 1

    last_data_row = max(excel_row - 1, 5)
    ws.auto_filter.ref = f"A4:F{last_data_row}"
    dv = DataValidation(
        type="list",
        formula1='"Pendiente,Cumplido,No Cumple"',
        allow_blank=False,
        showDropDown=False,
        showErrorMessage=True,
        errorTitle="Valor no permitido",
        error="Seleccione Pendiente, Cumplido o No Cumple.",
    )
    dv.promptTitle = "Cumplimiento"
    dv.prompt = "☐ Pendiente / ☑ Cumplido / ☒ No Cumple"
    dv.showInputMessage = True
    ws.add_data_validation(dv)
    dv.add(f"F5:F{last_data_row}")

    ws.conditional_formatting.add(
        f"F5:F{last_data_row}",
        FormulaRule(formula=['F5="Cumplido"'], fill=_fill("D9EDE4"), font=Font(color=GREEN, bold=True)),
    )
    ws.conditional_formatting.add(
        f"F5:F{last_data_row}",
        FormulaRule(formula=['F5="No Cumple"'], fill=_fill("F4D6D2"), font=Font(color=RED, bold=True)),
    )
    ws.conditional_formatting.add(
        f"F5:F{last_data_row}",
        FormulaRule(formula=['F5="Pendiente"'], fill=_fill("F4E9C8"), font=Font(color=AMBER, bold=True)),
    )

    widths = [22, 42, 36, 36, 42, 18]
    for index, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(index)].width = width
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "1:4"

    ws2 = wb.create_sheet("Entregables")
    ws2.merge_cells("A1:D1")
    t2 = ws2["A1"]
    t2.value = f"Entregables de gestión del proyecto — {expediente.code}"
    t2.font = _font(bold=True, color=WHITE, size=14)
    t2.fill = _fill(NAVY)
    t2.alignment = Alignment(horizontal="left", vertical="center")
    ws2.row_dimensions[1].height = 28

    headers2 = ["Numeral", "Entregable identificado", "Referencia documental", "Plazo de entrega"]
    _header(ws2, 3, headers2, TEAL)
    ws2.freeze_panes = "A4"
    ws2.auto_filter.ref = "A3:D3"

    row = 4
    for record in deliverables_df.to_dict("records"):
        values = [record["Numeral"], record["Entregable identificado"], record["Referencia documental"], record["Plazo de entrega"]]
        for col, value in enumerate(values, start=1):
            cell = ws2.cell(row=row, column=col, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = _border()
            cell.font = Font(name="Calibri", size=10, color=NAVY)
        row += 1

    if not deliverables_df.empty:
        table = Table(displayName="EntregablesGestion", ref=f"A3:D{row - 1}")
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws2.add_table(table)

    for index, width in enumerate([18, 48, 42, 32], start=1):
        ws2.column_dimensions[get_column_letter(index)].width = width

    ws3 = wb.create_sheet("Instrucciones")
    ws3["A1"] = "Uso de Checklist_Alcance_Proyecto.xlsx"
    ws3["A1"].font = _font(bold=True, color=NAVY, size=16)
    notes = [
        "Columna F es un desplegable interactivo: Pendiente / Cumplido / No Cumple.",
        "Las filas en beige indican contradicción contractual no resuelta (REQUIERE ACLARACIÓN).",
        "Las secciones doradas separan Alcance del Producto y Alcance del Proyecto.",
        "Hoja Entregables alimenta la EDT/WBS, plazos y evidencias de gestión.",
        "No agrupe requisitos distintos: cada fila es una condición verificable.",
        f"Expediente: {expediente.code} — {expediente.name}",
    ]
    for index, note in enumerate(notes, start=3):
        ws3[f"A{index}"] = note
        ws3[f"A{index}"].alignment = Alignment(wrap_text=True)
    ws3.column_dimensions["A"].width = 110

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
