from celery import Celery
from app.core.config import settings

celery_app = Celery("prevsolar", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.task_track_started = True
celery_app.conf.task_always_eager = settings.CELERY_TASK_ALWAYS_EAGER
celery_app.conf.task_eager_propagates = True
celery_app.autodiscover_tasks(["app.workers"])
