from dataclasses import asdict
from datetime import datetime, timezone

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.image import ImageStatus
from app.models.result import Result
from app.repositories import image_repository


@celery_app.task(bind=True, max_retries=3)
def process_image_task(
    self,
    image_id: int,
    threshold: float = 0.40,
    model_name: str = "default",
    gsd_m_px: float | None = None,
):
    from ai.pipeline import process_image

    db = SessionLocal()
    try:
        image = image_repository.get_by_id(db, image_id)
        if not image:
            return

        image_repository.update_status(db, image_id, ImageStatus.processing)

        pipeline_result = process_image(
            image.filepath,
            threshold=threshold,
            model_name=model_name,
            gsd_override=gsd_m_px,
        )

        # remove resultado anterior se existir (reprocessamento)
        db.query(Result).filter(Result.image_id == image_id).delete()
        db.flush()

        result = Result(
            image_id=image_id,
            panel_count=pipeline_result.panel_count,
            detected_area_m2=pipeline_result.detected_area_m2,
            estimated_kwh_month=pipeline_result.estimated_kwh_month,
            gsd_used_m_px=pipeline_result.gsd_used_m_px,
            mask_filepath=pipeline_result.mask_filepath,
            panels=[asdict(p) for p in pipeline_result.panels],
            processed_at=datetime.now(timezone.utc),
        )
        db.add(result)
        image_repository.update_status(db, image_id, ImageStatus.done)
        db.commit()

    except Exception as exc:
        db.rollback()
        image_repository.update_status(db, image_id, ImageStatus.error, str(exc)[:490])
        db.commit()
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()
