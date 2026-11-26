import logging
from pathlib import Path
import time

from redis import Redis
from sqlalchemy import text

from .database import open_session
from .panel_service import process_pending
from .settings import QUEUE_KEY, REDIS_URL

logger = logging.getLogger("ropeway.worker")
beat = Path("/tmp/panel-beat")


def main():
    logging.basicConfig(level=logging.INFO)
    queue = Redis.from_url(REDIS_URL, socket_timeout=4, socket_connect_timeout=3)
    while True:
        try:
            with open_session() as db:
                db.execute(text("SELECT 1"))
                has_work = process_pending(db)
            queue.ping()
            beat.touch()
            if not has_work:
                queue.brpop(QUEUE_KEY, timeout=3)
        except Exception:
            logger.exception("Worker dependency or sampler failed; durable candidate retained")
            time.sleep(4)


if __name__ == "__main__":
    main()
