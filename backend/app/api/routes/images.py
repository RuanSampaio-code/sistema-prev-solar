import math
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.repositories import image_repository
from app.schemas.image import ImageResponse, PaginatedImages
from app.workers.tasks import process_image_task

router = APIRouter()

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/tiff", "image/tif"}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def _validate_file(file: UploadFile):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Formato não suportado: {ext}")
    # TIFF pode chegar com content-type variado dependendo do browser/OS
    if ext in {".tif", ".tiff"}:
        return
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de arquivo inválido")


@router.post("/upload", response_model=list[ImageResponse], status_code=status.HTTP_202_ACCEPTED)
async def upload_images(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Máximo de 10 imagens por vez")

    results = []
    for file in files:
        _validate_file(file)

        content = await file.read()
        size_kb = len(content) / 1024
        max_kb = settings.MAX_UPLOAD_SIZE_MB * 1024

        if size_kb > max_kb:
            raise HTTPException(status_code=400, detail=f"Arquivo {file.filename} excede {settings.MAX_UPLOAD_SIZE_MB}MB")

        unique_name = f"{uuid.uuid4()}{Path(file.filename or 'img').suffix.lower()}"
        save_path = os.path.join(settings.UPLOAD_DIR, unique_name)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        with open(save_path, "wb") as f:
            f.write(content)

        image = image_repository.create(
            db,
            user_id=current_user.id,
            filename=unique_name,
            filepath=save_path,
            original_name=file.filename or unique_name,
            file_size_kb=round(size_kb, 2),
        )

        process_image_task.delay(image.id)
        results.append(image)

    return results


@router.get("", response_model=PaginatedImages)
def list_images(
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    status: str | None = None,
    order_by: str = "date",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = image_repository.list_paginated(db, page, page_size, search, status, order_by)
    return PaginatedImages(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size),
    )


@router.get("/{image_id}", response_model=ImageResponse)
def get_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image = image_repository.get_by_id(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return image


@router.post("/{image_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image = image_repository.get_by_id(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")

    from app.models.result import Result as ResultModel
    result = db.query(ResultModel).filter(ResultModel.image_id == image_id).first()
    if result:
        if result.mask_filepath and os.path.exists(result.mask_filepath):
            os.remove(result.mask_filepath)
        db.delete(result)

    if image.filepath and os.path.exists(image.filepath):
        os.remove(image.filepath)

    db.delete(image)
    db.commit()
