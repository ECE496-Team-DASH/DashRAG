"""Utility helpers for rough ETA estimation.

These estimates are intentionally conservative and are refined at runtime
using observed elapsed time plus progress signals.
"""

from __future__ import annotations


def _clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def estimate_index_total_ms(file_size_bytes: int | None, pages: int | None = None) -> int:
    """Estimate full indexing duration from file size and optional page count."""
    size_mb = 0.0
    if isinstance(file_size_bytes, int) and file_size_bytes > 0:
        size_mb = file_size_bytes / (1024 * 1024)

    page_count = pages or 0

    # Heuristic model calibrated to observed indexing times.
    # Smallest real PDFs (~5 pages, <1 MB) require ~2 minutes minimum because
    # NanoGraphRAG entity extraction makes multiple LLM calls per text chunk.
    # - High fixed overhead covers the LLM baseline cost
    # - Size and page count scale proportionally beyond the baseline
    estimate = int(90_000 + (size_mb * 40_000) + (page_count * 2_000))
    return _clamp(estimate, 120_000, 30 * 60_000)


def estimate_chat_total_ms(
    mode: str,
    prompt_length: int,
    ready_doc_count: int,
    ready_doc_pages: int,
) -> int:
    """Estimate end-to-end query duration.

    Global mode is typically the slowest because it maps and reduces
    cross-community context before final generation.
    """
    mode = (mode or "local").lower()
    mode_base = {
        "naive": 7_000,
        "local": 12_000,
        "global": 28_000,
    }.get(mode, 12_000)

    estimate = int(
        mode_base
        + max(prompt_length, 0) * 4
        + max(ready_doc_count, 0) * 900
        + max(ready_doc_pages, 0) * 35
    )
    return _clamp(estimate, 5_000, 10 * 60_000)


def estimate_remaining_ms(
    elapsed_ms: int,
    progress_percent: int | None,
    initial_total_ms: int,
) -> tuple[int, int]:
    """Return (estimated_total_ms, estimated_remaining_ms).

    Uses initial estimate first, then refines using observed elapsed/progress.
    """
    elapsed_ms = max(elapsed_ms, 0)
    progress = progress_percent if isinstance(progress_percent, int) else 0

    estimated_total_ms = max(initial_total_ms, elapsed_ms)

    if progress >= 5:
        observed_total = int(elapsed_ms / max(progress / 100.0, 0.01))
        # Give progressively more weight to observed data as progress increases.
        # At 5 % → ~5 % observed (initial dominates, observed is noisy).
        # At 50 % → 50 % each (balanced).
        # At 90 % → 90 % observed (we have good signal now).
        observed_weight = min(0.9, progress / 100.0)
        initial_weight = 1.0 - observed_weight
        estimated_total_ms = int(initial_weight * estimated_total_ms + observed_weight * observed_total)
        estimated_total_ms = max(estimated_total_ms, elapsed_ms)

    estimated_remaining_ms = max(0, estimated_total_ms - elapsed_ms)
    return estimated_total_ms, estimated_remaining_ms
