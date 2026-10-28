"""
ai_diagnoser.py — NetSage AI
-----------------------------
Sends one troubleshooting case (plus rule-checker findings) to Groq
and gets back a strict JSON diagnosis. A human always reviews the result
before it's accepted (see project Responsible AI log).
"""

import os
import csv
import json
from pathlib import Path


try:
    from src.checker import run_rule_checker
except ModuleNotFoundError:
    from checker import run_rule_checker


# Fields the AI's JSON reply must contain.
REQUIRED_FIELDS = [
    "root_cause",
    "confidence",
    "evidence",
    "next_command",
    "fix_steps",
]

# Valid confidence values.
VALID_CONFIDENCE_VALUES = ["high", "medium", "low"]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = str(PROJECT_ROOT / "prompts" / "diagnose_prompt.md")
CASES_CSV_PATH = str(PROJECT_ROOT / "dataset" / "cases.csv")

# Groq model.
MODEL_NAME = "openai/gpt-oss-120b"


def load_prompt_template(path: str = PROMPT_PATH) -> str:
    """Read the base instructions for the AI."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def build_user_message(case: dict, checker_result: dict) -> str:
    """Turn the case and checker findings into text for the model."""

    findings_text = "\n".join(
        f"- Rule: {item['rule']} | "
        f"Status: {item['status']} | "
        f"Details: {item['details']}"
        for item in checker_result.get("flagged_rules", [])
    ) or "None"

    return (
        f"Case ID: {case.get('case_id')}\n"
        f"Symptom: {case.get('symptom')}\n"
        f"Topology note: {case.get('topology_note')}\n"
        f"Show outputs: {case.get('show_outputs')}\n"
        f"Concept tag: {case.get('concept_tag')}\n"
        f"Severity: {case.get('severity')}\n\n"
        f"Rule checker matches found: "
        f"{checker_result.get('rule_matches_found')}\n"
        f"Rule checker findings:\n{findings_text}\n\n"
        "Respond with ONLY a JSON object with exactly these keys: "
        "root_cause, confidence, evidence, next_command, fix_steps. "
        "The 'confidence' value must be exactly one of: "
        "high, medium, low."
    )


def parse_ai_response(raw_text: str) -> dict:
    """
    Parse the model's reply as JSON and validate all required fields.
    """

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"AI response was not valid JSON: {e}"
        )

    missing = [
        field for field in REQUIRED_FIELDS
        if field not in data
    ]

    if missing:
        raise ValueError(
            f"AI response is missing required fields: {missing}"
        )

    confidence = str(
        data.get("confidence", "")
    ).strip().lower()

    if confidence not in VALID_CONFIDENCE_VALUES:
        raise ValueError(
            f"Invalid confidence value: "
            f"{data.get('confidence')!r}. "
            f"Must be one of {VALID_CONFIDENCE_VALUES}."
        )

    data["confidence"] = confidence

    return data


def diagnose_case(case: dict) -> dict:
    """
    Run the rule checker, call Groq, and return a diagnosis.
    """

    # 1. Run deterministic rule checker first.
    checker_result = run_rule_checker(case)

    # 2. Get Groq API key.
    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        return {
            "status": "error",
            "error": "GROQ_API_KEY environment variable is not set.",
            "checker_result": checker_result,
        }

    # 3. Load the AI prompt.
    try:
        prompt_template = load_prompt_template()

    except OSError as e:
        return {
            "status": "error",
            "error": f"Could not read {PROMPT_PATH}: {e}",
            "checker_result": checker_result,
        }

    # 4. Build the complete prompt.
    user_message = build_user_message(
        case,
        checker_result
    )

    full_prompt = (
        f"{prompt_template}\n\n{user_message}"
    )

    # 5. Call Groq. Import lazily so rule-only mode can run without the SDK.
    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": full_prompt,
                }
            ],
            temperature=0.2,
            response_format={
                "type": "json_object"
            },
        )

        raw_text = response.choices[0].message.content

    except Exception as e:
        return {
            "status": "error",
            "error": f"Groq API call failed: {e}",
            "checker_result": checker_result,
        }

    # 6. Parse and validate AI response.
    try:
        diagnosis = parse_ai_response(raw_text)

    except ValueError as e:
        return {
            "status": "error",
            "error": str(e),
            "checker_result": checker_result,
        }

    # 7. Return successful result.
    return {
        "status": "ok",
        "diagnosis": diagnosis,
        "checker_result": checker_result,
    }


def load_first_case(
    path: str = CASES_CSV_PATH
) -> dict:
    """Read the first real case from cases.csv."""

    with open(
        path,
        "r",
        encoding="utf-8",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:
            return row

    raise ValueError(
        f"No rows found in {path}"
    )


if __name__ == "__main__":
    # Manual test using a real case from dataset/cases.csv.
    case = load_first_case()

    result = diagnose_case(case)

    print(
        json.dumps(
            result,
            indent=2
        )
    )