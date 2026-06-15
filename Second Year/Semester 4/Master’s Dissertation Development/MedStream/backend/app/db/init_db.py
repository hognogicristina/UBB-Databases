import logging
from time import sleep

from sqlalchemy.exc import OperationalError

from app import models as app_models  # noqa: F401
from app.db.base import Base
from app.db.session import engine
from app.models import doctor as doctor_models  # noqa: F401
from app.models import patient as patient_models  # noqa: F401

logger = logging.getLogger(__name__)

DB_STARTUP_MAX_ATTEMPTS = 12
DB_STARTUP_RETRY_SECONDS = 5


def init_db(
    max_attempts: int = DB_STARTUP_MAX_ATTEMPTS,
    retry_seconds: int = DB_STARTUP_RETRY_SECONDS,
):
    for attempt in range(1, max_attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError:
            if attempt == max_attempts:
                raise

            logger.warning(
                "Database is not ready yet. Retrying startup initialization in %s seconds (%s/%s).",
                retry_seconds,
                attempt,
                max_attempts,
            )
            sleep(retry_seconds)
