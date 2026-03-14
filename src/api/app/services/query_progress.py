"""In-memory tracker for live message query progress.

This enables lightweight progress polling for active chat requests.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any


def _parse_iso_utc(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


_PROGRESS: dict[int, dict[str, Any]] = {}
_LOCK = RLock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_message_progress(
    message_id: int,
    session_id: int,
    estimated_total_ms: int,
    mode: str,
) -> None:
    with _LOCK:
        _PROGRESS[message_id] = {
            "message_id": message_id,
            "session_id": session_id,
            "status": "processing",
            "stage": "queued",
            "stage_label": "Queued",
            "progress_percent": 0,
            "estimated_total_ms": max(int(estimated_total_ms), 1),
            "estimated_remaining_ms": max(int(estimated_total_ms), 1),
            "elapsed_ms": 0,
            "completed_in_ms": None,
            "mode": mode,
            "started_at": _now_iso(),
            "updated_at": _now_iso(),
            "error": None,
        }


def update_message_progress(
    message_id: int,
    *,
    stage: str,
    stage_label: str,
    progress_percent: int,
    elapsed_ms: int,
    estimated_total_ms: int,
    estimated_remaining_ms: int,
) -> None:
    with _LOCK:
        existing = _PROGRESS.get(message_id)
        if not existing:
            return
        existing.update(
            {
                "stage": stage,
                "stage_label": stage_label,
                "progress_percent": max(0, min(100, int(progress_percent))),
                "elapsed_ms": max(0, int(elapsed_ms)),
                "estimated_total_ms": max(1, int(estimated_total_ms)),
                "estimated_remaining_ms": max(0, int(estimated_remaining_ms)),
                "updated_at": _now_iso(),
            }
        )


def complete_message_progress(message_id: int, completed_in_ms: int) -> None:
    with _LOCK:
        existing = _PROGRESS.get(message_id)
        if not existing:
            return
        existing.update(
            {
                "status": "complete",
                "stage": "complete",
                "stage_label": "Completed",
                "progress_percent": 100,
                "elapsed_ms": max(0, int(completed_in_ms)),
                "estimated_remaining_ms": 0,
                "completed_in_ms": max(0, int(completed_in_ms)),
                "updated_at": _now_iso(),
            }
        )


def fail_message_progress(message_id: int, elapsed_ms: int, error: str) -> None:
    with _LOCK:
        existing = _PROGRESS.get(message_id)
        if not existing:
            return
        existing.update(
            {
                "status": "error",
                "stage": "error",
                "stage_label": "Failed",
                "elapsed_ms": max(0, int(elapsed_ms)),
                "estimated_remaining_ms": 0,
                "error": error,
                "updated_at": _now_iso(),
            }
        )


def get_message_progress(message_id: int) -> dict[str, Any] | None:
    with _LOCK:
        item = _PROGRESS.get(message_id)
        if not item:
            return None

        data = dict(item)
        if data.get("status") == "processing":
            started_dt = _parse_iso_utc(data.get("started_at"))
            if started_dt:
                now_dt = datetime.now(timezone.utc)
                elapsed_ms = max(0, int((now_dt - started_dt).total_seconds() * 1000))
                estimated_total_ms = max(int(data.get("estimated_total_ms") or 0), elapsed_ms)
                estimated_remaining_ms = max(0, estimated_total_ms - elapsed_ms)
                data["elapsed_ms"] = elapsed_ms
                data["estimated_total_ms"] = estimated_total_ms
                data["estimated_remaining_ms"] = estimated_remaining_ms
                data["updated_at"] = now_dt.isoformat()

        return data


def clear_message_progress(message_id: int) -> None:
    with _LOCK:
        _PROGRESS.pop(message_id, None)
