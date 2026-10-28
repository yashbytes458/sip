"""NetSage AI human-review and responsible-AI audit logging."""

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
REVIEWS_CSV_PATH = LOG_DIR / "human_reviews.csv"
RESPONSIBLE_AI_CSV_PATH = LOG_DIR / "responsible_ai_log.csv"

VALID_DECISIONS = {"Accepted", "Edited", "Rejected"}
REVIEW_HEADERS = [
    "case_id", "decision", "ai_root_cause", "corrected_root_cause",
    "reviewer_notes", "timestamp",
]
AUDIT_HEADERS = [
    "case_id", "decision", "ai_root_cause", "human_corrected_root_cause",
    "reason_for_correction", "timestamp",
]


def init_log_files() -> None:
    """Create the project log directory and CSV files with headers if absent."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for path, headers in (
        (REVIEWS_CSV_PATH, REVIEW_HEADERS),
        (RESPONSIBLE_AI_CSV_PATH, AUDIT_HEADERS),
    ):
        if not path.exists() or path.stat().st_size == 0:
            with path.open("w", newline="", encoding="utf-8") as file:
                csv.writer(file).writerow(headers)


def log_review(
    case_id: str,
    decision: str,
    ai_root_cause: str,
    corrected_root_cause: Optional[str] = "",
    reviewer_notes: Optional[str] = "",
) -> dict[str, Any]:
    """Append a review; edited/rejected results also enter the audit log."""
    init_log_files()
    normalized_decision = (decision or "").strip().capitalize()
    if normalized_decision not in VALID_DECISIONS:
        raise ValueError(f"Invalid decision: {decision!r}. Choose Accepted, Edited, or Rejected.")

    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    corrected = (corrected_root_cause or "").strip()
    notes = (reviewer_notes or "").strip()

    with REVIEWS_CSV_PATH.open("a", newline="", encoding="utf-8") as file:
        csv.writer(file).writerow(
            [case_id, normalized_decision, ai_root_cause, corrected, notes, timestamp]
        )

    if normalized_decision in {"Edited", "Rejected"}:
        with RESPONSIBLE_AI_CSV_PATH.open("a", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow(
                [case_id, normalized_decision, ai_root_cause, corrected, notes, timestamp]
            )

    return {
        "status": "ok",
        "case_id": case_id,
        "decision": normalized_decision,
        "timestamp": timestamp,
        "logged_to_responsible_ai": normalized_decision in {"Edited", "Rejected"},
    }


def get_review_summary() -> dict[str, Any]:
    """Return counts and the percentage of diagnoses accepted by reviewers."""
    init_log_files()
    counts = {"Accepted": 0, "Edited": 0, "Rejected": 0, "Total": 0}
    with REVIEWS_CSV_PATH.open("r", newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            decision = (row.get("decision") or "").strip().capitalize()
            counts["Total"] += 1
            if decision in VALID_DECISIONS:
                counts[decision] += 1
    agreement_rate = counts["Accepted"] / counts["Total"] * 100 if counts["Total"] else 0.0
    return {"counts": counts, "agreement_rate_percent": round(agreement_rate, 2)}


def get_responsible_ai_logs() -> list[dict[str, str]]:
    """Return responsible-AI audit records, newest entries last."""
    init_log_files()
    with RESPONSIBLE_AI_CSV_PATH.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))
