from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def checkpoint_path(checkpoint_dir: str | Path, step: str) -> Path:
    return Path(checkpoint_dir) / f"{step}.json"


def is_completed(checkpoint_dir: str | Path, step: str) -> bool:
    return checkpoint_path(checkpoint_dir, step).exists()


def mark_completed(checkpoint_dir: str | Path, step: str, extra: dict[str, Any] | None = None) -> None:
    payload = {"step": step, "completed_at": datetime.now(UTC).isoformat()}
    if extra:
        payload.update(extra)
    p = checkpoint_path(checkpoint_dir, step)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def should_skip(resume: bool, force: bool, checkpoint_dir: str | Path, step: str) -> bool:
    if force:
        return False
    return resume and is_completed(checkpoint_dir, step)
