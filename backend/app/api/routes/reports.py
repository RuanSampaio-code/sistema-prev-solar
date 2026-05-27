import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.image import Image, ImageStatus
from app.models.result import Result
from app.models.user import User

router = APIRouter()


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
    writer.writerow(["Unidade Consumidora", "Quantidade de Painéis", "Área Detectada (m²)",
                     "Potencial Energético (kWh/mês)", "Data do Processamento"])

    for image, result in rows:
        writer.writerow([
            image.consumer_unit,
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
