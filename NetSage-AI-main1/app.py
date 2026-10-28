from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ai_diagnoser import diagnose_case
from src.checker import run_rule_checker
from src.review_logger import (
    get_responsible_ai_logs,
    get_review_summary,
    log_review,
)

DATASET_PATH = ROOT / "dataset" / "cases.csv"
REVIEWS_PATH = ROOT / "logs" / "human_reviews.csv"
AUDIT_PATH = ROOT / "logs" / "responsible_ai_log.csv"

st.set_page_config(page_title="NetSage AI", page_icon="🌐", layout="wide")
st.markdown(
    """
    <style>
    :root { color-scheme: dark; }
    .stApp { background: #0b1120; color: #e5edf8; }
    [data-testid="stHeader"] { background: rgba(11,17,32,.92); }
    [data-testid="stSidebar"] { background: #111a2b; border-right: 1px solid #26354b; }
    [data-testid="stSidebar"] * { color: #e5edf8; }
    .block-container { padding-top: 1.35rem; padding-bottom: 2.5rem; max-width: 1500px; }
    .hero { padding: 1.5rem 1.7rem; border-radius: 20px;
            background: linear-gradient(120deg, #132b4c 0%, #1b2140 55%, #252044 100%);
            border: 1px solid #314968; margin-bottom: 1.2rem; box-shadow: 0 12px 32px rgba(0,0,0,.18); }
    .hero h1 { margin: 0; color: #f8fbff; font-size: 2.25rem; letter-spacing: -.035em; }
    .hero p { margin: .5rem 0 0; color: #c1d1e8; font-size: 1.02rem; }
    h1, h2, h3, h4, p, label, .stMarkdown, [data-testid="stCaptionContainer"] { color: #e5edf8; }
    [data-testid="stMetric"] { background: #141f31 !important; border: 1px solid #2a3a52 !important;
        border-radius: 15px !important; padding: 17px 18px !important; box-shadow: 0 6px 18px rgba(0,0,0,.12); }
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p { color: #aebed4 !important; opacity: 1 !important; }
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] div { color: #f4f8ff !important; }
    [data-testid="stMetricDelta"] { color: #80e1c1 !important; }
    [data-testid="stDataFrame"], [data-testid="stTable"] { border: 1px solid #2a3a52; border-radius: 12px; overflow: hidden; }
    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
    [data-testid="stSelectbox"] div[data-baseweb="select"], [data-testid="stNumberInput"] input {
        background: #111b2b !important; color: #edf4ff !important; border-color: #344760 !important; }
    [data-testid="stTextInput"] input::placeholder, [data-testid="stTextArea"] textarea::placeholder { color: #8ea1bb !important; }
    .stButton > button, [data-testid="stFormSubmitButton"] button { border-radius: 10px; font-weight: 650; }
    .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
        background: linear-gradient(90deg,#2878e5,#7258d8); color: white; border: 0; }
    div[data-testid="stAlert"] { border-radius: 12px; }
    hr { border-color: #2b3a50; }
    a { color: #82b9ff !important; }
    code { color: #b7d8ff !important; }
    @media (max-width: 700px) { .hero { padding: 1.1rem; } .hero h1 { font-size: 1.8rem; } }
    </style>
    <div class="hero"><h1>🌐 NetSage AI</h1>
    <p>Network intelligence workspace · deterministic diagnostics · AI-assisted root-cause analysis · human-reviewed recommendations</p></div>
    """,
    unsafe_allow_html=True,
)


def get_api_key() -> str:
    """Read the Groq API key from environment variables or Streamlit secrets."""
    key = os.getenv("GROQ_API_KEY", "").strip()
    if key:
        return key
    try:
        return str(st.secrets.get("GROQ_API_KEY", "")).strip()
    except Exception:
        # Streamlit secrets may not be configured in a local installation.
        return ""


@st.cache_data(show_spinner=False)
def load_cases() -> list[dict[str, str]]:
    """Load dataset cases and validate the columns required by this UI."""
    if not DATASET_PATH.is_file():
        return []
    with DATASET_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {"case_id", "symptom", "topology_note", "show_outputs"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                "dataset/cases.csv must contain these columns: "
                + ", ".join(sorted(required))
            )
        return [dict(row) for row in reader if any((v or "").strip() for v in row.values())]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))
    except (OSError, csv.Error, UnicodeError):
        return []


def show_checker(result: dict[str, Any] | None) -> None:
    result = result or {}
    flags = result.get("flagged_rules") or []
    if flags:
        st.warning(f"{len(flags)} deterministic rule finding(s) flagged.")
        st.dataframe(
            [
                {
                    "Rule": item.get("rule", "Unknown"),
                    "Status": item.get("status", "Unknown"),
                    "Details": item.get("details", "No details provided"),
                }
                for item in flags
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success(
            "No deterministic rule findings flagged. This does not guarantee "
            "that the network is correctly configured."
        )

    checks = result.get("all_checks") or []
    if checks:
        with st.expander("View all deterministic checks"):
            st.dataframe(
                [
                    {
                        "Status": item.get("status", "Unknown"),
                        "Rule": item.get("rule", "Unknown"),
                        "Details": item.get("details", ""),
                    }
                    for item in checks
                ],
                use_container_width=True,
                hide_index=True,
            )


try:
    cases = load_cases()
except (OSError, csv.Error, UnicodeError, ValueError) as exc:
    st.error(f"Could not load dataset/cases.csv: {exc}")
    st.stop()

if not cases:
    st.error(
        "Dataset not found or empty. Ensure dataset/cases.csv exists and "
        "contains valid case rows inside the project folder."
    )
    st.stop()

api_key = get_api_key()

with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Open section",
        ["Troubleshoot", "Dashboard & Logs", "About / Setup"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption(f"Loaded {len(cases)} cases from dataset/cases.csv")
    st.markdown(
        "**AI service:** "
        + ("🟢 Groq API key detected" if api_key else "🟠 Rule checks only")
    )

if page == "Troubleshoot":
    st.subheader("Troubleshoot a network case")
    mode = st.radio(
        "Input method",
        ["Choose a sample case", "Enter a custom case"],
        horizontal=True,
    )

    if mode == "Choose a sample case":
        labels = {
            f"{case.get('case_id') or 'Unknown'} · "
            f"{case.get('concept_tag') or 'Network case'}": case
            for case in cases
        }
        chosen_label = st.selectbox("Select a case from the dataset", list(labels))
        selected = dict(labels[chosen_label])
        with st.expander("View original case details"):
            st.write("**Symptom**", selected.get("symptom", ""))
            st.write("**Topology**", selected.get("topology_note", ""))
            st.code(selected.get("show_outputs", "") or "No command output provided")

        with st.form("case_form"):
            symptom = st.text_area("Symptom", selected.get("symptom", ""), height=100)
            topology = st.text_area(
                "Topology notes", selected.get("topology_note", ""), height=100
            )
            outputs = st.text_area(
                "Cisco show-command outputs / evidence",
                selected.get("show_outputs", ""),
                height=180,
            )
            run_troubleshooting = st.form_submit_button(
                "Run troubleshooting", type="primary", use_container_width=True
            )
        case = {
            **selected,
            "symptom": symptom,
            "topology_note": topology,
            "show_outputs": outputs,
        }
    else:
        with st.form("custom_case_form"):
            case_id = st.text_input("Case ID", "CUSTOM-001")
            symptom = st.text_area("Symptom", placeholder="Describe what is failing...", height=100)
            topology = st.text_area(
                "Topology notes", placeholder="Devices, interfaces, VLANs, IP addresses...", height=100
            )
            outputs = st.text_area(
                "Cisco show-command outputs / evidence",
                placeholder="Paste relevant show command output...",
                height=180,
            )
            concept = st.text_input("Concept tag", "General troubleshooting")
            severity = st.selectbox("Severity", ["Low", "Medium", "High", "Critical"])
            run_troubleshooting = st.form_submit_button(
                "Run troubleshooting", type="primary", use_container_width=True
            )
        case = {
            "case_id": case_id.strip() or "CUSTOM-001",
            "symptom": symptom,
            "topology_note": topology,
            "show_outputs": outputs,
            "concept_tag": concept,
            "severity": severity,
            "expected_fault": "",
            "osi_layer": "",
        }

    if run_troubleshooting:
        if not any(str(case.get(field, "")).strip() for field in ("symptom", "topology_note", "show_outputs")):
            st.error("Enter at least a symptom, topology note, or command output first.")
        else:
            try:
                with st.spinner("Running deterministic network checks..."):
                    checker_result = run_rule_checker(case)
                st.session_state["active_case"] = case
                st.session_state["checker_result"] = checker_result

                if api_key:
                    with st.spinner("Requesting structured diagnosis from Groq..."):
                        diagnosis_result = diagnose_case(case)
                    st.session_state["diagnosis_result"] = diagnosis_result
                else:
                    st.session_state["diagnosis_result"] = {
                        "status": "error",
                        "error": "GROQ_API_KEY is not configured. Deterministic rule checks are available.",
                    }
            except Exception as exc:
                st.session_state["active_case"] = case
                st.session_state["checker_result"] = {}
                st.session_state["diagnosis_result"] = {
                    "status": "error",
                    "error": f"Troubleshooting failed: {exc}",
                }

    if "checker_result" in st.session_state and "active_case" in st.session_state:
        active = st.session_state["active_case"]
        st.divider()
        st.subheader(f"Results · {active.get('case_id', 'Case')}")
        show_checker(st.session_state.get("checker_result", {}))
        ai_result = st.session_state.get("diagnosis_result", {}) or {}

        if ai_result.get("status") == "ok" and isinstance(ai_result.get("diagnosis"), dict):
            diagnosis = ai_result["diagnosis"]
            st.markdown("### AI diagnosis")
            confidence = str(diagnosis.get("confidence", "low")).capitalize()
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("**Likely root cause**")
                st.write(diagnosis.get("root_cause") or "Not provided")
            with col2:
                st.metric("AI confidence", confidence)

            st.markdown("**Evidence**")
            st.write(diagnosis.get("evidence") or "Not provided")
            st.markdown("**Next diagnostic command**")
            st.code(str(diagnosis.get("next_command") or "Not provided"))
            st.markdown("**Suggested fix steps**")
            fix_steps = diagnosis.get("fix_steps", [])
            if isinstance(fix_steps, list):
                for index, step in enumerate(fix_steps, 1):
                    st.write(f"{index}. {step}")
            else:
                st.write(str(fix_steps))

            st.info(
                "Human review is required. Verify commands and proposed changes "
                "in your lab before applying them."
            )
            with st.form("human_review_form"):
                decision = st.radio(
                    "Review decision", ["Accepted", "Edited", "Rejected"], horizontal=True
                )
                corrected = st.text_area("Corrected root cause (required if edited)", "")
                notes = st.text_area("Reviewer notes", "")
                submit_review = st.form_submit_button("Save human review", type="primary")

            if submit_review:
                if decision == "Edited" and not corrected.strip():
                    st.error("Provide the corrected root cause when choosing Edited.")
                else:
                    try:
                        review = log_review(
                            str(active.get("case_id", "CUSTOM")),
                            decision,
                            str(diagnosis.get("root_cause", "")),
                            corrected,
                            notes,
                        )
                        st.success(
                            f"Review saved: {review.get('decision', decision)} "
                            f"at {review.get('timestamp', 'unknown time')}."
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not save review: {exc}")
        else:
            st.warning("AI diagnosis is unavailable. You can still use deterministic findings above.")
            if ai_result.get("error"):
                st.caption(str(ai_result["error"]))
            st.markdown(
                "To enable AI diagnosis, set `GROQ_API_KEY` in your environment "
                "or Streamlit secrets, then restart Streamlit."
            )

elif page == "Dashboard & Logs":
    st.subheader("Review dashboard")
    try:
        summary = get_review_summary() or {}
    except Exception as exc:
        summary = {}
        st.error(f"Could not load review summary: {exc}")

    counts = summary.get("counts", {}) or {}
    metrics = [
        ("Total reviews", counts.get("Total", 0)),
        ("Accepted", counts.get("Accepted", 0)),
        ("Edited", counts.get("Edited", 0)),
        ("Rejected", counts.get("Rejected", 0)),
        ("Agreement rate", f"{summary.get('agreement_rate_percent', 0)}%"),
    ]
    for col, (label, value) in zip(st.columns(5), metrics):
        col.metric(label, value)

    reviews = read_csv_rows(REVIEWS_PATH)
    try:
        audit = get_responsible_ai_logs() or []
    except Exception as exc:
        audit = []
        st.error(f"Could not load responsible AI audit log: {exc}")

    left, right = st.columns(2)
    with left:
        st.markdown("### Human review history")
        if reviews:
            st.dataframe(reviews[::-1], use_container_width=True, hide_index=True)
            st.download_button(
                "Download human reviews CSV",
                REVIEWS_PATH.read_bytes(),
                file_name="human_reviews.csv",
                mime="text/csv",
            )
        else:
            st.info("No human reviews have been recorded yet.")

    with right:
        st.markdown("### Responsible AI audit log")
        if audit:
            st.dataframe(audit[::-1], use_container_width=True, hide_index=True)
            if AUDIT_PATH.is_file():
                st.download_button(
                    "Download responsible AI log CSV",
                    AUDIT_PATH.read_bytes(),
                    file_name="responsible_ai_log.csv",
                    mime="text/csv",
                )
        else:
            st.info("No edited or rejected AI diagnoses recorded yet.")

else:
    st.subheader("About NetSage AI")
    st.write(
        "NetSage AI combines deterministic checks for common networking issues "
        "with an optional Groq-powered structured diagnosis. Human review "
        "decisions are recorded for accountability."
    )
    st.markdown("**Run locally on Windows**")
    st.code(
        "python -m venv .venv\n"
        ".venv\\Scripts\\activate\n"
        "python -m pip install -r requirements.txt\n"
        "streamlit run app.py"
    )
    st.markdown("**Enable AI diagnosis in Windows Command Prompt (CMD)**")
    st.code('set GROQ_API_KEY=your_groq_api_key\npython -m streamlit run app.py')
    st.caption(
        "Never share your API key or commit it to source control. Rule-checker "
        "findings are heuristic and may miss faults or flag evidence incorrectly."
    )
