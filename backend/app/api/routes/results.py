from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.image import Image, ImageStatus
from app.models.result import Result
from app.models.user import User
from app.schemas.image import DashboardStats

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    total_images = db.query(func.count(Image.id)).scalar() or 0
    total_processed = db.query(func.count(Image.id)).filter(Image.status == ImageStatus.done).scalar() or 0
    total_panels = db.query(func.sum(Result.panel_count)).scalar() or 0
    highest_kwh = db.query(func.max(Result.estimated_kwh_month)).scalar() or 0.0

    ranking_rows = (
        db.query(Image.consumer_unit, func.max(Result.estimated_kwh_month).label("kwh"))
        .join(Result)
        .group_by(Image.consumer_unit)
        .order_by(func.max(Result.estimated_kwh_month).desc())
        .limit(10)
        .all()
    )
    ranking = [{"consumer_unit": r.consumer_unit, "kwh_month": r.kwh} for r in ranking_rows]

    return DashboardStats(
        total_images=total_images,
        total_processed=total_processed,
        total_panels=int(total_panels),
        highest_kwh_month=round(float(highest_kwh), 2),
        ranking=ranking,
    )
