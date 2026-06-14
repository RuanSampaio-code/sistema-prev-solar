import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.image import Image, ImageStatus
from app.models.result import Result
from app.models.user import User

router = APIRouter()

# ── cores do tema PrevSolar ──────────────────────────────────────────────────
_COLOR_HEADER_BG = "0F172A"   # slate-900
_COLOR_HEADER_FG = "FFFFFF"
_COLOR_PRIMARY   = "F59E0B"   # amber-400
_COLOR_ROW_ALT   = "F8FAFC"   # slate-50
_COLOR_TOTAL_BG  = "FEF3C7"   # amber-100
_COLOR_BORDER    = "E2E8F0"   # slate-200

_THIN = Side(style="thin", color=_COLOR_BORDER)
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def _col(ws, col: int, width: float):
    ws.column_dimensions[get_column_letter(col)].width = width


@router.get("/xlsx")
def export_xlsx(
    image_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Image, Result).join(Result).filter(Image.status == ImageStatus.done)
    if image_id:
        q = q.filter(Image.id == image_id)

    rows = q.order_by(Result.estimated_kwh_month.desc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Relatório PrevSolar"

    # ── Título ────────────────────────────────────────────────────────────────
    ws.merge_cells("A1:E1")
    title_cell = ws["A1"]
    title_cell.value = "PrevSolar — Análise de Painéis Fotovoltaicos"
    title_cell.font = Font(name="Calibri", size=16, bold=True, color=_COLOR_PRIMARY)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32

    ws.merge_cells("A2:E2")
    sub_cell = ws["A2"]
    sub_cell.value = f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}  |  {len(rows)} registro(s)"
    sub_cell.font = Font(name="Calibri", size=10, italic=True, color="64748B")
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 18

    ws.row_dimensions[3].height = 8  # espaçamento

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    headers = ["Imagem", "Qtd. Painéis", "Área Detectada (m²)", "Potencial (kWh/mês)", "Processado em"]
    header_fill = PatternFill("solid", fgColor=_COLOR_HEADER_BG)
    header_font = Font(name="Calibri", size=11, bold=True, color=_COLOR_HEADER_FG)

    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=4, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = _BORDER
    ws.row_dimensions[4].height = 22

    # ── Dados ─────────────────────────────────────────────────────────────────
    alt_fill = PatternFill("solid", fgColor=_COLOR_ROW_ALT)
    data_font = Font(name="Calibri", size=10)

    total_panels = 0
    total_area = 0.0
    total_kwh = 0.0

    for i, (image, result) in enumerate(rows):
        row_num = i + 5
        fill = alt_fill if i % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")

        values = [
            image.original_name,
            result.panel_count,
            round(result.detected_area_m2, 2),
            round(result.estimated_kwh_month, 2),
            result.processed_at.strftime("%d/%m/%Y %H:%M"),
        ]
        alignments = ["left", "center", "center", "center", "center"]

        for col, (val, align) in enumerate(zip(values, alignments), start=1):
            cell = ws.cell(row=row_num, column=col, value=val)
            cell.fill = fill
            cell.font = data_font
            cell.alignment = Alignment(horizontal=align, vertical="center")
            cell.border = _BORDER

        # destaca kWh em negrito
        kwh_cell = ws.cell(row=row_num, column=4)
        kwh_cell.font = Font(name="Calibri", size=10, bold=True, color="059669")

        total_panels += result.panel_count
        total_area += result.detected_area_m2
        total_kwh += result.estimated_kwh_month

    # ── Linha de totais ───────────────────────────────────────────────────────
    if rows:
        total_row = len(rows) + 5
        total_fill = PatternFill("solid", fgColor=_COLOR_TOTAL_BG)
        total_font = Font(name="Calibri", size=10, bold=True)

        totals = ["TOTAL", total_panels, round(total_area, 2), round(total_kwh, 2), ""]
        for col, val in enumerate(totals, start=1):
            cell = ws.cell(row=total_row, column=col, value=val)
            cell.fill = total_fill
            cell.font = total_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = _BORDER

    # ── Larguras das colunas ──────────────────────────────────────────────────
    _col(ws, 1, 40)
    _col(ws, 2, 14)
    _col(ws, 3, 20)
    _col(ws, 4, 22)
    _col(ws, 5, 18)

    # Congela a linha de cabeçalho
    ws.freeze_panes = "A5"

    # ── Serializa ─────────────────────────────────────────────────────────────
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"prevsolar_relatorio_{image_id or 'completo'}.xlsx"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/csv")
def export_csv(
    image_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Image, Result).join(Result).filter(Image.status == ImageStatus.done)
    if image_id:
        q = q.filter(Image.id == image_id)

    rows = q.order_by(Result.estimated_kwh_month.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Imagem", "Quantidade de Painéis", "Área Detectada (m²)",
                     "Potencial Energético (kWh/mês)", "Data do Processamento"])

    for image, result in rows:
        writer.writerow([
            image.original_name,
            result.panel_count,
            f"{result.detected_area_m2:.2f}",
            f"{result.estimated_kwh_month:.2f}",
            result.processed_at.strftime("%d/%m/%Y %H:%M"),
        ])

    output.seek(0)
    filename = f"prevsolar_resultado_{image_id or 'completo'}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
