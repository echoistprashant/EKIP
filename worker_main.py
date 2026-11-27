"""
Standalone Ingestion Worker Entrypoint.
Run with:
    python worker_main.py
or:
    python -m app.workers.worker

Allows decoupling background document parsing, chunking, and vector embedding
from the web server when scaling out to a dedicated worker tier.
"""
import asyncio
import logging
from app.workers.worker import run_ingestion_worker_loop

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("ekip.worker_main")
    logger.info("Initializing standalone worker process...")
    try:
        asyncio.run(run_ingestion_worker_loop())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker process terminated by user or OS.")
