from sqlalchemy.orm import Session

from app.models.image import Image, ImageStatus


def create(db: Session, user_id: int, filename: str, filepath: str,
           original_name: str, file_size_kb: float) -> Image:
    image = Image(
        user_id=user_id,
        filename=filename,
        filepath=filepath,
        original_name=original_name,
        file_size_kb=file_size_kb,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def get_by_id(db: Session, image_id: int) -> Image | None:
    return db.query(Image).filter(Image.id == image_id).first()


def update_status(db: Session, image_id: int, status: ImageStatus, error: str | None = None):
    db.query(Image).filter(Image.id == image_id).update(
        {"status": status, "error_message": error}
    )
    db.commit()


def list_paginated(db: Session, page: int, page_size: int, search: str | None,
                   status: str | None, order_by: str) -> tuple[list[Image], int]:
    q = db.query(Image)
    if search:
        q = q.filter(Image.original_name.ilike(f"%{search}%"))
    if status:
        q = q.filter(Image.status == status)

    total = q.count()

    if order_by == "energy":
        from app.models.result import Result
        q = q.outerjoin(Result).order_by(Result.estimated_kwh_month.desc().nullslast())
    else:
        q = q.order_by(Image.uploaded_at.desc())

    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total
