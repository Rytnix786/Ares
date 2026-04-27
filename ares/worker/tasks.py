from __future__ import annotations

from celery import Celery

celery_app = Celery("ares", broker="redis://localhost:6379/0", backend="redis://localhost:6379/0")
celery_app.conf.task_always_eager = False


@celery_app.task(name="ares.evaluate")
def evaluate_task(payload: dict) -> dict:
    return {"status": "queued", "payload": payload}