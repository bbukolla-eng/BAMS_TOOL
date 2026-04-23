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
    from sqlalchemy import func, select

    from core.database import AsyncSessionLocal
    from models.learning import FeedbackEvent, MLTrainingJob

    async with AsyncSessionLocal() as db:
        for model_type in ["mechanical", "electrical", "plumbing"]:
            count_result = await db.execute(
                select(func.count(FeedbackEvent.id)).where(
                    FeedbackEvent.event_type == "symbol_correction",
                    FeedbackEvent.is_training_candidate.is_(True),
                    FeedbackEvent.used_in_training_job_id.is_(None),
                )
            )
            count = count_result.scalar() or 0
            log.info(f"Model {model_type}: {count} new feedback events (need {MIN_FEEDBACK_FOR_TRAINING})")

            if count >= MIN_FEEDBACK_FOR_TRAINING:
                job = MLTrainingJob(
                    model_type=f"yolo_{model_type}",
                    status="running",
                    triggered_by="scheduled",
                    feedback_count=count,
                )
                db.add(job)
                await db.flush()
                job_id = job.id
                await db.commit()

                log.info(f"Starting retraining job {job_id} for {model_type}")
                success = await _run_training(model_type, job_id)

                # Mark feedback events as used
                async with AsyncSessionLocal() as db2:
                    result2 = await db2.execute(
                        select(FeedbackEvent).where(
                            FeedbackEvent.event_type == "symbol_correction",
                            FeedbackEvent.is_training_candidate.is_(True),
                            FeedbackEvent.used_in_training_job_id.is_(None),
                        )
                    )
                    for ev in result2.scalars().all():
                        ev.used_in_training_job_id = job_id

                    result3 = await db2.execute(
                        select(MLTrainingJob).where(MLTrainingJob.id == job_id)
                    )
                    finished_job = result3.scalar_one_or_none()
                    if finished_job:
                        finished_job.status = "completed" if success else "failed"
                        finished_job.was_promoted = success  # True when best.pt was copied to current.pt
                        finished_job.completed_at = __import__("datetime").datetime.utcnow()
                    await db2.commit()
                return

        await db.commit()


async def _run_training(model_type: str, job_id: int) -> bool:
    """Invoke the YOLO training script in a subprocess to avoid event loop conflicts."""
    import asyncio
    import sys
    from pathlib import Path

    script = Path(__file__).parent.parent.parent / "ml" / "training" / "train_yolo.py"
    if not script.exists():
        log.error("Training script not found: %s", script)
        return False

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(script),
            "--model-type", model_type,
            "--epochs", "50",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=7200)
        if proc.returncode == 0:
            log.info("Training succeeded for %s", model_type)
            return True
        else:
            log.error("Training failed for %s: %s", model_type, stderr.decode()[-2000:])
            return False
    except TimeoutError:
        log.error("Training timed out for %s", model_type)
        return False
    except Exception as e:
        log.error("Training error for %s: %s", model_type, e)
        return False


async def _accuracy_report_async():
    from sqlalchemy import func, select

    from core.database import AsyncSessionLocal
    from models.drawing import MaterialRun, Symbol
    from models.learning import FeedbackEvent

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

        verified_syms = await db.execute(select(func.count(Symbol.id)).where(Symbol.is_verified.is_(True)))
        verified_runs = await db.execute(select(func.count(MaterialRun.id)).where(MaterialRun.is_verified.is_(True)))

        report = {
            "total_symbols_detected": total_syms.scalar() or 0,
            "total_runs_detected": total_runs.scalar() or 0,
            "verified_symbols": verified_syms.scalar() or 0,
            "verified_runs": verified_runs.scalar() or 0,
            "total_corrections": total_corrections,
        }
        log.info(f"Weekly accuracy report: {report}")
