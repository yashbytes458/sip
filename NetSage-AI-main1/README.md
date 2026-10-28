# NetSage AI 🌐🤖

> **AI-Assisted Network Troubleshooting Helper with Human-in-the-Loop Review**  
> *Built for Cisco Packet Tracer and Networking Lab Scenarios*

---

## 📌 Project Overview

Junior network engineers frequently memorize Cisco commands but struggle to isolate root causes when multi-layer faults occur (e.g. PC gets an IP address but cannot reach a server—is it a VLAN, Gateway, Routing, ACL, NAT, DHCP, or DNS fault?).

**NetSage AI** assists network students and engineers by:
1. Reading **symptoms**, **topology notes**, and Cisco **`show` command outputs**.
2. Running a **deterministic Python rule checker** for common configuration syntax/state mistakes.
3. Invoking a **structured Groq AI diagnosis** that returns root cause, confidence, evidence citations, next diagnostic commands, and remediation steps.
4. Enforcing a **mandatory Human Review step** (`Accepted`, `Edited`, `Rejected`) before any fix is accepted, keeping an audit log of all human corrections.
5. Displaying real-time **Dashboard Metrics** and an agreement score.

---

## 🏗️ Architecture & Component Flow

```
[ Lab Case Data (dataset/cases.csv) ]
                  │
                  ▼
      ┌───────────────────────┐
      │ Python Rule Checker   │ ──► (Catches down interfaces, subnet/VLAN mismatches, missing routes)
      │  (src/checker.py)     │
      └───────────────────────┘
                  │
                  ▼
      ┌───────────────────────┐
      │  AI Diagnosis Engine  │ ──► (Combines prompts/diagnose_prompt.md + case evidence + Groq API)
      │ (src/ai_diagnoser.py) │
      └───────────────────────┘
                  │
                  ▼
      ┌───────────────────────┐
      │ Human Review Logger   │ ◄── [Mandatory Human Oversight: Accept / Edit / Reject]
      │(src/review_logger.py) │
      └───────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
[ logs/human_reviews.csv ]  [ logs/responsible_ai_log.csv ]
        │                   │
        └─────────┬─────────┘
                  ▼
[ Web Dashboard UI (http://127.0.0.1:8000/) ]
```

---

## 📂 Project Directory Structure

```
CIsco_vip_project/
├── dataset/
│   └── cases.csv                # 30 structured Packet Tracer lab cases (7 required fields)
├── prompts/
│   └── diagnose_prompt.md       # Engineered prompt with JSON schema & 3 worked examples
├── src/
│   ├── checker.py               # Deterministic rule checker (6 required checks)
│   ├── ai_diagnoser.py          # Groq API integration & JSON validator
│   ├── review_logger.py         # Human review audit logger & Responsible AI tracker
│   ├── api.py                   # FastAPI application serving REST endpoints & static UI
│   └── static/
│       └── index.html           # Interactive web dashboard & review interface
├── logs/
│   ├── human_reviews.csv        # Log of all human review decisions
│   └── responsible_ai_log.csv   # Documented audit log of human corrections
├── requirements.txt             # Python dependencies (fastapi, uvicorn, groq)
└── README.md                    # Project documentation & presentation guide
```

---

## 🚀 Setup & Execution Guide

### 1. Prerequisites
- Python 3.10+ installed.

### 2. Environment Setup
Activate the project virtual environment:
```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

### 3. Configure  Groq API Key
Set your Groq API key in your terminal session:
```powershell
$env:GROQ_API_KEY="your_actual_Groq_api_key_here"
```

### 4. Start the Application Server
```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api:app --reload
```

### 5. Access the Web Dashboard
Open your browser and navigate to:
👉 **`http://127.0.0.1:8000/`**

---

## 🔍 Required PDF Deliverables Checklist

| Deliverable | File Location | Status | Description |
| :--- | :--- | :---: | :--- |
| **Case Dataset** | [`dataset/cases.csv`](dataset/cases.csv) | ✅ Complete | 30 lab cases across VLAN, Gateway, DHCP, DNS, Routing, ACL, NAT, Wireless. |
| **Prompt Library** | [`prompts/diagnose_prompt.md`](prompts/diagnose_prompt.md) | ✅ Complete | Strict JSON output format with 3 worked examples and low-confidence fallback. |
| **Python Checker** | [`src/checker.py`](src/checker.py) | ✅ Complete | Generic deterministic checks for 6 common configuration errors. |
| **Dashboard** | `http://127.0.0.1:8000/` | ✅ Complete | Visual summary of issue types, severity, and AI vs. human agreement rate. |
| **Responsible AI Log** | [`logs/responsible_ai_log.csv`](logs/responsible_ai_log.csv) | ✅ Complete | Audit log recording cases where AI diagnoses were edited or rejected by a human. |

---

## 🎬 5–10 Minute Presentation & Demo Video Script

Use this outline for your college project video or presentation:

### **Part 1: Introduction & Problem Statement (1–2 minutes)**
- Explain the challenge junior network engineers face in connecting symptoms (e.g., ping timeouts) to the actual OSI layer root cause.
- Introduce **NetSage AI** as an assistive tool built on the principle of **Human-in-the-Loop (HITL)** AI.

### **Part 2: Interactive Lab Diagnosis Demo (2–3 minutes)**
1. Open `http://127.0.0.1:8000/` in the browser.
2. Select **`CASE-VLAN-01`** (*Wrong Access VLAN*).
3. Click **⚡ Run NetSage AI Diagnosis**.
4. Show how:
   - The **Python Rule Checker** flagged `VLAN_MISCONFIGURATION` (Port configured for Access VLAN 20, but intended VLAN is 10).
   - The **Groq AI Model** identified the Layer 2 root cause and provided exact Cisco IOS fix commands (`switchport access vlan 10`).

### **Part 3: Human Review & Responsible AI Logging (2–3 minutes)**
1. For a correct diagnosis, click **✓ Accept Fix** $\rightarrow$ Show the agreement score update to 100%.
2. Select a complex or ambiguous case (e.g., `CASE-ACL-02`).
3. Click **✎ Edit Diagnosis** $\rightarrow$ Refine the explanation and add notes $\rightarrow$ Save.
4. Scroll down to the **Responsible AI Correction Log** and show that the correction was recorded with timestamp and rationale.

### **Part 4: Conclusion & Key Learnings (1 minute)**
- Summarize how combining **deterministic rule checking** with **LLM reasoning** provides high-accuracy diagnostics while maintaining safety through mandatory human oversight.
