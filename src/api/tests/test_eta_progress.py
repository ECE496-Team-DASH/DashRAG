from app.services.eta_estimator import (
    estimate_index_total_ms,
    estimate_chat_total_ms,
    estimate_remaining_ms,
)
import time
from app.services.query_progress import (
    start_message_progress,
    update_message_progress,
    complete_message_progress,
    fail_message_progress,
    get_message_progress,
    clear_message_progress,
)


def test_index_estimate_scales_with_file_size():
    small = estimate_index_total_ms(1 * 1024 * 1024, pages=5)
    large = estimate_index_total_ms(5 * 1024 * 1024, pages=5)
    assert large > small


def test_index_estimate_minimum_is_two_minutes():
    # Even a tiny PDF must produce at least a 2-minute estimate because
    # NanoGraphRAG entity extraction has high fixed LLM overhead.
    tiny = estimate_index_total_ms(file_size_bytes=10 * 1024, pages=1)
    assert tiny >= 120_000, f"Expected >= 120 000 ms (2 min), got {tiny} ms"


def test_chat_estimate_scales_with_mode_and_context_size():
    local_small = estimate_chat_total_ms("local", prompt_length=40, ready_doc_count=1, ready_doc_pages=10)
    global_large = estimate_chat_total_ms("global", prompt_length=120, ready_doc_count=4, ready_doc_pages=120)
    assert global_large > local_small


def test_remaining_estimate_refines_from_progress():
    initial_total = 20_000
    total_ms, remaining_ms = estimate_remaining_ms(
        elapsed_ms=5_000,
        progress_percent=50,
        initial_total_ms=initial_total,
    )
    assert total_ms >= 5_000
    assert 0 <= remaining_ms <= total_ms


def test_query_progress_lifecycle():
    msg_id = 99_999
    clear_message_progress(msg_id)

    start_message_progress(
        message_id=msg_id,
        session_id=123,
        estimated_total_ms=120_000,
        mode="local",
    )
    started = get_message_progress(msg_id)
    assert started is not None
    assert started["status"] == "processing"
    assert started["estimated_total_ms"] == 120_000

    time.sleep(1.1)
    ticking = get_message_progress(msg_id)
    assert ticking is not None
    assert ticking["elapsed_ms"] >= 1000
    assert ticking["estimated_remaining_ms"] < started["estimated_remaining_ms"]

    update_message_progress(
        msg_id,
        stage="querying_graphrag",
        stage_label="Querying knowledge graph",
        progress_percent=45,
        elapsed_ms=3_200,
        estimated_total_ms=12_000,
        estimated_remaining_ms=8_800,
    )
    updated = get_message_progress(msg_id)
    assert updated is not None
    assert updated["stage"] == "querying_graphrag"
    assert updated["progress_percent"] == 45

    complete_message_progress(msg_id, completed_in_ms=9_100)
    done = get_message_progress(msg_id)
    assert done is not None
    assert done["status"] == "complete"
    assert done["completed_in_ms"] == 9_100
    assert done["progress_percent"] == 100

    fail_message_progress(msg_id, elapsed_ms=9_500, error="boom")
    failed = get_message_progress(msg_id)
    assert failed is not None
    assert failed["status"] == "error"
    assert failed["error"] == "boom"

    clear_message_progress(msg_id)
    assert get_message_progress(msg_id) is None
