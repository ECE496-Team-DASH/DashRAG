import json
import secrets
import time
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[3]
PDF_DIR = ROOT / "pdfs-for-testing"


def pick_pdf() -> Path:
    for candidate in sorted(PDF_DIR.glob("*.pdf")):
        return candidate
    raise RuntimeError(f"No PDF found in {PDF_DIR}")


def register_and_login() -> dict:
    email = f"realtime-{secrets.token_hex(5)}@example.com"
    password = "test123"

    r = requests.post(
        f"{BASE_URL}/auth/register",
        json={"email": email, "password": password},
        timeout=20,
    )
    r.raise_for_status()

    r = requests.post(
        f"{BASE_URL}/auth/token",
        data={"username": email, "password": password},
        timeout=20,
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def ensure_session(headers: dict) -> int:
    r = requests.post(
        f"{BASE_URL}/sessions",
        json={"title": "Realtime Progress Verification"},
        headers=headers,
        timeout=20,
    )
    r.raise_for_status()
    return int(r.json()["id"])


def verify_document_progress_ticks(headers: dict, sid: int, pdf_path: Path) -> tuple[int, bool, str]:
    with pdf_path.open("rb") as f:
        r = requests.post(
            f"{BASE_URL}/documents/upload?sid={sid}",
            files={"file": f},
            headers=headers,
            timeout=60,
        )
    r.raise_for_status()
    doc = r.json()
    doc_id = int(doc["id"])

    stream = requests.get(
        f"{BASE_URL}/documents/progress-stream?sid={sid}&doc_id={doc_id}",
        headers=headers,
        stream=True,
        timeout=240,
    )
    stream.raise_for_status()

    elapsed_samples: list[int] = []
    terminal_status = "unknown"

    for raw in stream.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data: "):
            continue
        payload = json.loads(raw[6:])

        if payload.get("event") == "error":
            terminal_status = "error"
            break

        if payload.get("event") == "complete":
            terminal_status = str(payload.get("status") or "unknown")
            break

        if payload.get("status") in {"inserting", "downloading"}:
            elapsed = int(payload.get("elapsed_ms") or 0)
            elapsed_samples.append(elapsed)
            if len(elapsed_samples) >= 5:
                # Enough samples to verify real-time ticking.
                break

    increasing = any(
        b > a for a, b in zip(elapsed_samples, elapsed_samples[1:])
    )
    return doc_id, increasing, terminal_status


def verify_query_progress_ticks(headers: dict, sid: int) -> bool:
    # Wait for at least one ready document.
    ready = False
    for _ in range(180):
        r = requests.get(f"{BASE_URL}/documents?sid={sid}", headers=headers, timeout=20)
        r.raise_for_status()
        docs = r.json()
        if docs and any(d.get("status") == "ready" for d in docs):
            ready = True
            break
        time.sleep(1)

    if not ready:
        raise RuntimeError("No ready document available; cannot verify query progress")

    prompt = (
        "Provide a detailed synthesis with explicit reasoning steps about the uploaded paper. "
        "Include major concepts, dependencies, and explain each in depth. " * 6
    )
    r = requests.post(
        f"{BASE_URL}/messages?sid={sid}",
        json={"content": prompt, "mode": "global"},
        headers=headers,
        timeout=60,
    )
    r.raise_for_status()
    message_id = int(r.json()["message_id"])

    processing_elapsed: list[int] = []
    for _ in range(90):
        p = requests.get(
            f"{BASE_URL}/messages/progress?sid={sid}&message_id={message_id}",
            headers=headers,
            timeout=20,
        )
        p.raise_for_status()
        payload = p.json()
        status = payload.get("status")
        if status == "processing":
            processing_elapsed.append(int(payload.get("elapsed_ms") or 0))
        if status in {"complete", "error"}:
            break
        time.sleep(1)

    # Need at least two processing samples to prove real-time increment while in-flight.
    if len(processing_elapsed) < 2:
        return False

    return any(b > a for a, b in zip(processing_elapsed, processing_elapsed[1:]))


def main() -> None:
    pdf = pick_pdf()
    headers = register_and_login()
    sid = ensure_session(headers)

    doc_id, doc_elapsed_increasing, terminal_status = verify_document_progress_ticks(headers, sid, pdf)
    print(f"document_id={doc_id} document_elapsed_increasing={doc_elapsed_increasing} terminal_status={terminal_status}")

    query_elapsed_increasing = verify_query_progress_ticks(headers, sid)
    print(f"query_elapsed_increasing={query_elapsed_increasing}")

    if not doc_elapsed_increasing:
        raise RuntimeError("Document elapsed_ms did not increase in real time")
    if not query_elapsed_increasing:
        raise RuntimeError("Query elapsed_ms did not increase in real time")

    print("PASS realtime progress verification")


if __name__ == "__main__":
    main()
