#!/usr/bin/env python3
"""
Clean duplicate scheduler tasks.

Duplicate key:
    persona_id + task_type + schedule + platform

Keeps the most recently updated/created task in each duplicate group.
Default mode is dry-run.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select

# Ensure project root is importable when running as a standalone script.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from avatarfactory.core.database.connection import get_session, init_database  # noqa: E402
from avatarfactory.core.database.models import ScheduledTaskModel  # noqa: E402


@dataclass
class TaskLite:
    id: str
    persona_id: Optional[str]
    task_type: str
    schedule: str
    platform: Optional[str]
    created_at: datetime
    updated_at: datetime

    @property
    def dedupe_key(self) -> Tuple[str, str, str, str]:
        return (
            self.persona_id or "__system__",
            self.task_type,
            self.schedule,
            self.platform or "__none__",
        )

    @property
    def rank_ts(self) -> datetime:
        return self.updated_at or self.created_at


def _format_key(key: Tuple[str, str, str, str]) -> str:
    persona_id, task_type, schedule, platform = key
    return (
        f"persona_id={persona_id}, task_type={task_type}, "
        f"schedule='{schedule}', platform={platform}"
    )


async def _load_tasks() -> List[TaskLite]:
    async with get_session() as session:
        rows = await session.execute(select(ScheduledTaskModel))
        models = rows.scalars().all()
        return [
            TaskLite(
                id=m.id,
                persona_id=m.persona_id,
                task_type=m.task_type,
                schedule=m.schedule,
                platform=m.platform,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in models
        ]


def _plan_deletions(tasks: List[TaskLite]) -> Tuple[Dict[Tuple[str, str, str, str], List[TaskLite]], List[str]]:
    grouped: Dict[Tuple[str, str, str, str], List[TaskLite]] = {}
    for task in tasks:
        grouped.setdefault(task.dedupe_key, []).append(task)

    delete_ids: List[str] = []
    for key, group in grouped.items():
        if len(group) <= 1:
            continue
        sorted_group = sorted(group, key=lambda t: (t.rank_ts, t.created_at, t.id), reverse=True)
        keep = sorted_group[0]
        drop = sorted_group[1:]
        print(f"[DUPLICATE] {_format_key(key)}")
        print(f"  keep: {keep.id} (updated_at={keep.updated_at}, created_at={keep.created_at})")
        for t in drop:
            print(f"  drop: {t.id} (updated_at={t.updated_at}, created_at={t.created_at})")
            delete_ids.append(t.id)

    return grouped, delete_ids


async def _apply_delete(delete_ids: List[str]) -> int:
    if not delete_ids:
        return 0
    async with get_session() as session:
        deleted = 0
        for task_id in delete_ids:
            model = await session.get(ScheduledTaskModel, task_id)
            if model is not None:
                await session.delete(model)
                deleted += 1
        return deleted


async def _run(kb_path: str, apply: bool) -> int:
    await init_database(kb_path=kb_path)
    tasks = await _load_tasks()
    print(f"Loaded {len(tasks)} scheduled task(s).")

    _, delete_ids = _plan_deletions(tasks)
    if not delete_ids:
        print("No duplicates found.")
        return 0

    print(f"Found {len(delete_ids)} duplicate task(s) to remove.")
    if not apply:
        print("Dry-run mode: no changes applied. Use --apply to delete duplicates.")
        return 0

    deleted = await _apply_delete(delete_ids)
    print(f"Applied cleanup: deleted {deleted} duplicate task(s).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean duplicate scheduler tasks")
    parser.add_argument(
        "--kb-path",
        default="./knowledges",
        help="Knowledge base directory path (default: ./knowledges)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete duplicates. Without this flag, runs dry-run only.",
    )
    args = parser.parse_args()

    return asyncio.run(_run(kb_path=args.kb_path, apply=args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
