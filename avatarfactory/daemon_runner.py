"""
Background daemon runner for AvatarFactory.

Supports two modes:
- scheduler: Run only the scheduler as a background daemon
- full: Run the full FastAPI service with scheduler

This module can be invoked by:
- `avatarfactory daemon start --background` (scheduler mode)
- `avatarfactory serve` (full mode)
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime


def setup_logging(mode: str = "scheduler"):
    """Set up logging for the daemon."""
    log_dir = os.path.join(
        os.getenv("AVATARFACTORY_KB_PATH", "./knowledges"),
        "scheduler",
        "logs"
    )
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"{mode}_{datetime.now().strftime('%Y%m%d')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ]
    )

    return logging.getLogger(f"avatarfactory.{mode}")


def run_scheduler_only():
    """Run only the scheduler daemon."""
    logger = setup_logging("scheduler")
    logger.info("Starting AvatarFactory scheduler daemon")

    try:
        from avatarfactory.scheduler import Scheduler, SchedulerConfig

        config = SchedulerConfig(
            data_dir=os.path.join(
                os.getenv("AVATARFACTORY_KB_PATH", "./knowledges"),
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
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.exception(f"Scheduler error: {e}")
        sys.exit(1)


def run_full_service(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """
    Run the full FastAPI service with integrated scheduler.

    Args:
        host: Host to bind to
        port: Port to listen on
        reload: Enable auto-reload for development
    """
    logger = setup_logging("service")
    logger.info(f"Starting AvatarFactory service on {host}:{port}")

    try:
        import uvicorn
    except ImportError:
        logger.error("uvicorn is required for the service. Install with: pip install uvicorn")
        sys.exit(1)

    try:
        uvicorn.run(
            "avatarfactory.service.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.exception(f"Service error: {e}")
        sys.exit(1)


def main():
    """Main entry point with mode selection."""
    parser = argparse.ArgumentParser(
        description="AvatarFactory Daemon Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  scheduler    Run only the background scheduler
  full         Run the full FastAPI service with scheduler

Examples:
  python -m avatarfactory.daemon_runner --mode scheduler
  python -m avatarfactory.daemon_runner --mode full --port 8000
        """
    )
    parser.add_argument(
        "--mode",
        choices=["scheduler", "full"],
        default="full",
        help="Run mode: scheduler (background only) or full (API + scheduler)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (full mode only)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (full mode only)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development (full mode only)"
    )

    args = parser.parse_args()

    if args.mode == "scheduler":
        run_scheduler_only()
    else:
        run_full_service(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
