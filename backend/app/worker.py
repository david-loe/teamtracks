import logging
import signal
import time

from sqlalchemy import select

from app.config import get_settings
from app.db.session import SessionLocal
from app.domain import ConversionJobStatus
from app.models.conversion_job import ConversionJob
from app.services.conversion import ConversionService
from app.services.storage import StorageService


logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("teamtracks.worker")
POLL_INTERVAL_SECONDS = 2


def process_next_job(conversion_service: ConversionService) -> bool:
    with SessionLocal() as db:
        job = db.scalar(
            select(ConversionJob)
            .where(ConversionJob.status == ConversionJobStatus.QUEUED.value)
            .order_by(ConversionJob.created_at.asc(), ConversionJob.id.asc())
        )
        if job is None:
            return False

        logger.info(
            "processing %s job %s for song %s stem %s target key %s",
            job.job_type,
            job.id,
            job.song_id,
            job.stem_id,
            job.target_key,
        )
        conversion_service.process_job(db, job.id)
        return True


def run() -> None:
    stopping = False
    settings = get_settings()
    storage = StorageService(settings.storage_root, settings.source_root)
    conversion_service = ConversionService(storage)

    def request_stop(signum: int, _frame: object) -> None:
        nonlocal stopping
        logger.info("received signal %s, stopping worker", signum)
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    logger.info("worker started")
    while not stopping:
        try:
            processed = process_next_job(conversion_service)
        except Exception:
            logger.exception("conversion worker failed while processing queued job")
            processed = False
        if not processed:
            time.sleep(POLL_INTERVAL_SECONDS)
    logger.info("worker stopped")


if __name__ == "__main__":
    run()
