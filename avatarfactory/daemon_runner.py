"""
Background daemon runner for AvatarFactory scheduler.

This module is invoked by `avatarfactory daemon start --background` to run
the scheduler as a detached background process.
"""

import asyncio
import os
import sys
import signal
import logging
from datetime import datetime


def setup_logging():
    """Set up logging for the daemon."""
    log_dir = os.path.join(
        os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base"),
        "scheduler",
        "logs"
    )
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"daemon_{datetime.now().strftime('%Y%m%d')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
        ]
    )

    return logging.getLogger("avatarfactory.daemon")


def main():
    """Run the scheduler daemon."""
    logger = setup_logging()
    logger.info("Starting AvatarFactory daemon")

    try:
        from avatarfactory.scheduler import Scheduler, SchedulerConfig

        config = SchedulerConfig(
            data_dir=os.path.join(
                os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base"),
                "scheduler"
            )
        )
        scheduler = Scheduler(config)

        tasks = scheduler.list_tasks()
        logger.info(f"Loaded {len(tasks)} scheduled tasks")
        for task in tasks:
            logger.info(f"  - {task.name} ({task.schedule})")

        logger.info("Scheduler started, running in blocking mode")

        # Use blocking=True which handles the event loop correctly
        scheduler.start(blocking=True)

    except KeyboardInterrupt:
        logger.info("Daemon stopped by user")
    except Exception as e:
        logger.exception(f"Daemon error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
