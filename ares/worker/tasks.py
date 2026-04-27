from __future__ import annotations

from celery import Celery

from ares.config import settings

celery_app = Celery("ares", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.task_always_eager = False


@celery_app.task(name="ares.evaluate")
def evaluate_task(payload: dict) -> dict:
    return {"status": "queued", "payload": payload}