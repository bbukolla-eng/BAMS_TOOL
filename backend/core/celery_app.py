from celery import Celery
from celery.schedules import crontab

from core.config import settings

celery_app = Celery(
    "bams",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "workers.process_drawing",
        "workers.process_spec",
        "workers.run_takeoff",
        "workers.train_model",
        "workers.generate_proposal",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,
)

celery_app.conf.beat_schedule = {
    "weekly-model-retraining": {
        "task": "workers.train_model.check_and_retrain",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),  # Sunday 2AM
    },
    "accuracy-report": {
        "task": "workers.train_model.generate_accuracy_report",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),  # Monday 8AM
    },
}
