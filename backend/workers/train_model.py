"""
Self-learning: weekly model retraining and accuracy reporting.
"""
import logging
from core.celery_app import celery_app

log = logging.getLogger(__name__)

MIN_FEEDBACK_FOR_TRAINING = 50


@celery_app.task(name="workers.train_model.check_and_retrain")
def check_and_retrain():
    import asyncio
    asyncio.run(_check_and_retrain_async())


@celery_app.task(name="workers.train_model.generate_accuracy_report")
def generate_accuracy_report():
    import asyncio
    asyncio.run(_accuracy_report_async())


async def _check_and_retrain_async():
    from core.database import AsyncSessionLocal
    from models.learning import FeedbackEvent, MLTrainingJob
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as db:
        # Count unprocessed feedback events by model type
        for model_type in ["yolo_mechanical", "yolo_electrical", "yolo_plumbing"]:
            count_result = await db.execute(
                select(func.count(FeedbackEvent.id)).where(
                    FeedbackEvent.event_type == "symbol_correction",
                    FeedbackEvent.is_training_candidate == True,
                    FeedbackEvent.used_in_training_job_id == None,
                )
            )
            count = count_result.scalar() or 0

            log.info(f"Model {model_type}: {count} new feedback events")

            if count >= MIN_FEEDBACK_FOR_TRAINING:
                log.info(f"Triggering retraining for {model_type} with {count} examples")
                job = MLTrainingJob(
                    model_type=model_type,
                    status="pending",
                    triggered_by="scheduled",
                    feedback_count=count,
                )
                db.add(job)
                await db.flush()
                # In production: dispatch to a dedicated GPU training worker
                # For now just log the intent
                log.info(f"Training job {job.id} created for {model_type}")

        await db.commit()


async def _accuracy_report_async():
    from core.database import AsyncSessionLocal
    from models.learning import MLTrainingJob, FeedbackEvent
    from models.drawing import Symbol, MaterialRun
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as db:
        # Count recent corrections
        corrections = await db.execute(
            select(func.count(FeedbackEvent.id)).where(
                FeedbackEvent.event_type.in_(["symbol_correction", "run_correction"])
            )
        )
        total_corrections = corrections.scalar() or 0

        total_syms = await db.execute(select(func.count(Symbol.id)))
        total_runs = await db.execute(select(func.count(MaterialRun.id)))

        verified_syms = await db.execute(select(func.count(Symbol.id)).where(Symbol.is_verified == True))
        verified_runs = await db.execute(select(func.count(MaterialRun.id)).where(MaterialRun.is_verified == True))

        report = {
            "total_symbols_detected": total_syms.scalar() or 0,
            "total_runs_detected": total_runs.scalar() or 0,
            "verified_symbols": verified_syms.scalar() or 0,
            "verified_runs": verified_runs.scalar() or 0,
            "total_corrections": total_corrections,
        }
        log.info(f"Weekly accuracy report: {report}")
