#!/usr/bin/env python
"""RQ worker entry point.

Run with:
    python -m app.queue.worker
or
    rq worker pipeline --url $REDIS_URL
"""
import logging
import os

import redis
from rq import Worker, Queue, Connection

from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    conn = redis.Redis.from_url(settings.redis_url)
    queues = ["pipeline"]
    log.info(f"Starting RQ worker on queues: {queues}")
    with Connection(conn):
        worker = Worker(list(map(Queue, queues)))
        worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
