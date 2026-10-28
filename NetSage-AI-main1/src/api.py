"""
api.py — NetSage AI backend API
---------------------------------
A small FastAPI app that exposes one endpoint, POST /diagnose, which
accepts a troubleshooting case as JSON and returns the AI diagnosis
plus the rule-checker results. All actual work (rule checks + calling
Gemini) happens in ai_diagnoser.diagnose_case().

Run locally with:
    uvicorn api:app --reload
(from inside the src/ folder, or use "src.api:app" from the project root)
"""

import os
import csv
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from src.ai_diagnoser import diagnose_case
except ModuleNotFoundError:
    from ai_diagnoser import diagnose_case

try:
    from src.review_logger import log_review, get_review_summary, get_responsible_ai_logs
except ModuleNotFoundError:
    from review_logger import log_review, get_review_summary, get_responsible_ai_logs

app = FastAPI(title="NetSage AI API")


class CaseInput(BaseModel):
    """
    Shape of one troubleshooting case, matching the columns in
    dataset/cases.csv. All fields are required strings.
    """
    case_id: str
    symptom: str
    topology_note: str
    show_outputs: str
    expected_fault: str
    osi_layer: str
    concept_tag: str
    severity: str


class ReviewInput(BaseModel):
    """
    Shape of a human review entry submitted for a case.
    """
    case_id: str
    decision: str  # Accepted, Edited, or Rejected
    ai_root_cause: str
    corrected_root_cause: Optional[str] = ""
    reviewer_notes: Optional[str] = ""


@app.post("/diagnose")
def diagnose(case: CaseInput):
    """
    Accepts one case as JSON, runs the rule checker + AI diagnosis,
    and returns everything the frontend needs to display and let a
    human reviewer accept/edit/reject the result.
    """
    try:
        case_dict = case.model_dump()
        result = diagnose_case(case_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}")

    return result


@app.post("/review")
def submit_review(review: ReviewInput):
    """
    Records a human review decision (Accepted, Edited, Rejected)
    and logs corrections to the Responsible AI log.
    """
    try:
        res = log_review(
            case_id=review.case_id,
            decision=review.decision,
            ai_root_cause=review.ai_root_cause,
            corrected_root_cause=review.corrected_root_cause,
            reviewer_notes=review.reviewer_notes
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log review: {e}")


@app.get("/cases")
def get_all_cases():
    """Returns all 30 troubleshooting cases from dataset/cases.csv."""
    cases_path = "dataset/cases.csv"
    if not os.path.exists(cases_path):
        raise HTTPException(status_code=404, detail="dataset/cases.csv not found")
    with open(cases_path, mode="r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@app.get("/responsible-ai-log")
def get_responsible_ai_log_entries():
    """Returns all documented human corrections from the Responsible AI log."""
    return get_responsible_ai_logs()


@app.get("/summary")
def get_dashboard_summary():
    """Returns issue breakdown and AI vs Human agreement rate."""
    return get_review_summary()


# Mount static files directory if available
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_dashboard():
    """Serves the NetSage AI web dashboard."""
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "NetSage AI API is running. Visit /docs for API documentation."}


@app.get("/health")
def health():
    """Simple check to confirm the API is running."""
    return {"status": "ok"}
