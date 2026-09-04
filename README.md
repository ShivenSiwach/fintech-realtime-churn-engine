# 🚀 B2B Fintech Real-Time Churn Engine

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/ShivenSiwach/fintech-realtime-churn-engine)
![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green.svg)

An event-driven machine learning inference microservice designed to evaluate SME churn risk and accounting ERP sync health in real-time from corporate card transaction telemetry.

---

## 📌 1. Business Problem & Domain Context

When scaling a B2B corporate expense platform (e.g., scaling past 10,000+ SMEs), customer churn rarely happens abruptly. In B2B SaaS and Fintech, accounts suffer from **"silent churn"** — a slow-burning pattern of disengagement that shows up in behavioral signals long before a cancellation email arrives:

```
[Declined Card Velocity] ──► [Receipt Compliance Drops] ──► [Ignored ERP Sync Errors] ──► [Account Cancellation]
```

- **Interchange Bleed:** Card usage drops from ~50 swipes a week to single digits, quietly shrinking weekly interchange revenue.
- **Workflow Abandonment:** When employees stop uploading receipts, the automated ledger sync (e.g., Fortnox, Visma, Xero) breaks.
- **The Lag Problem:** Monthly churn reports identify churn *after* the account is already lost — by the time a human notices, the revenue is gone.

This service acts as an **in-line event evaluator** that scores every card-swipe webhook in **<15ms**, assigning a dynamic risk score and triggering proactive retention workflows before the customer leaves — so Customer Success teams can intervene early instead of reading about it in a monthly report.

---

## 🏗️ 2. System Architecture

```
                                ┌──────────────────────────────────────────────┐
                                │               FastAPI Gateway                 │
[Transaction Webhook] ─────────►│ 1. Pydantic Payload Validation                │
 (Amount, SME ID, Telemetry)    │ 2. Feature Extraction                         │
                                │ 3. ML Model In-Memory Inference (Joblib)      │
                                └──────────────────────┬───────────────────────┘
                                                        │
                                                        ▼
                                        ┌──────────────────────────────┐
                                        │     Risk Evaluation Engine   │
                                        ├──────────────────────────────┤
                                        │ Score >= 0.70 ──► CRITICAL   │
                                        │ Score >= 0.40 ──► ELEVATED   │
                                        │ Score <  0.40 ──► LOW        │
                                        └──────────────────────────────┘
```

**Stack:**
- **FastAPI** — asynchronous webhook ingestion and routing
- **Scikit-Learn / Joblib** — real-time risk probability scoring (Random Forest classifier)
- **Pydantic** — strict schema validation to prevent corrupt financial telemetry from reaching the model
- **Docker / DevContainers** — fully containerized for one-click cloud deployment

---
## 📈 Model & Data



**⚠️ Synthetic data disclosure:** this model is trained on synthetically generated telemetry (`data/generate_mock_data.py`), not real Mynt or customer data. It exists to demonstrate the inference architecture and feature engineering approach — not to make production churn claims. The feature relationships (declining transaction velocity, dropping receipt compliance, rising ERP sync errors → churn) are hand-modeled from the domain narrative above, then a Random Forest is trained to recover that signal.

**Held-out test performance** (80/20 split, stratified, `random_state=42` — reproducible via `python data/evaluate_model.py`):

| Metric | Score |
|---|---|
| Precision (churned) | 0.885 |
| Recall (churned) | 0.622 |
| F1 (churned) | 0.730 |
| ROC-AUC | 0.990 |

Base rate: ~7.4% of accounts churn in the synthetic set, so this is a class-imbalanced problem — precision/recall on the minority class matter more than raw accuracy (which is a misleading 97%).

**Risk band calibration** — checking whether the `CRITICAL` / `ELEVATED` / `LOW` thresholds in the Risk Evaluation Engine actually track real risk on the test set:

| Band | Threshold | Accounts | Actual churn rate in band |
|---|---|---|---|
| CRITICAL | score ≥ 0.70 | 37 | 94.6% |
| ELEVATED | 0.40 ≤ score < 0.70 | 27 | 70.4% |
| LOW | score < 0.40 | 936 | 2.1% |

The bands are well-separated on synthetic data, which validates the threshold design — but recall of 0.62 means roughly a third of true churners are being under-scored. On real data, that recall gap is where I'd want to prioritize feature work.
## 📂 3. Project Structure

```
fintech-realtime-churn-engine/
├── .devcontainer/
│   └── devcontainer.json         # Automated cloud dev environment & port forwarding
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI application & webhook endpoints
│   └── schemas.py                # Pydantic request/response validation schemas
├── data/
│   └── generate_mock_data.py     # B2B telemetry data synthesis & model training
├── model/
│   └── churn_model.pkl           # Serialized Random Forest classifier artifact
├── Dockerfile                    # Multi-stage production container manifest
├── requirements.txt              # Pinned production dependencies
├── .gitignore                    # Prevents .venv, cache, and artifact leaks
└── README.md                     # Technical architecture documentation
```

---

## 📊 4. Telemetry Features & Data Dictionary

| Feature Name | Type | Description | Churn Impact |
|---|---|---|---|
| `weekly_transaction_count` | `Integer` | Total corporate card transactions in the trailing 7 days. | Inverse: Low swipe volume indicates disengagement. |
| `receipt_upload_ratio` | `Float (0.0 - 1.0)` | Ratio of settled expenses with verified receipt images. | Inverse: Drop below 0.50 indicates workflow abandonment. |
| `erp_sync_errors` | `Integer` | Unresolved sync errors with external accounting software. | Direct: Higher sync failures correlate with platform frustration. |
| `days_since_last_active` | `Float` | Days elapsed since an admin/cardholder accessed the app. | Direct: Inactivity is a primary leading indicator of churn. |

---

## 🧪 5. Live Interactive Demo (No Setup Required)

You do not need to install Python, configure environments, or clone anything locally to test this service.

1. Click the **[Open in GitHub Codespaces](https://codespaces.new/ShivenSiwach/fintech-realtime-churn-engine)** badge at the top of this page.
2. GitHub will automatically spin up a secure cloud container, install dependencies, train the baseline model artifact, and launch the server on port `8000`.
3. Once the terminal says `Application startup complete`, open the forwarded port URL and append `/docs` to reach the interactive Swagger UI.

### Sample Test Payload

Paste this into the `POST /webhooks/transaction-evaluation` endpoint to simulate an SME in trouble:

```json
{
  "transaction_id": "tx_se_88219",
  "sme_id": "sme_stockholm_041",
  "amount_sek": 4500.0,
  "merchant_category": "Cloud Services",
  "weekly_transaction_count": 2,
  "receipt_upload_ratio": 0.15,
  "erp_sync_errors": 6,
  "days_since_last_active": 14.0
}
```

### Expected Real-Time Response (200 OK)

```json
{
  "sme_id": "sme_stockholm_041",
  "transaction_id": "tx_se_88219",
  "churn_risk_score": 0.8641,
  "risk_level": "CRITICAL",
  "action_required": true,
  "summary": "High churn signal: Severe drop in transaction velocity and sync failures."
}
```

---

## 💻 6. Local Setup & Container Deployment

### Option A: Local Python Environment

```bash
# 1. Clone repository
git clone https://github.com/ShivenSiwach/fintech-realtime-churn-engine.git
cd fintech-realtime-churn-engine

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Generate mock dataset and train artifact
python data/generate_mock_data.py

# 5. Start API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Option B: Docker Container

```bash
# Build the container image
docker build -t fintech-churn-engine:latest .

# Run the containerized service
docker run -d -p 8000:8000 --name churn-engine fintech-churn-engine:latest

# Verify health status
curl http://localhost:8000/health
```

The API will be live at `http://localhost:8000/docs`.

---

## 🔒 7. API Specification

### `GET /health`
Returns the status of the service and confirms the ML artifact is loaded into memory.
- **Status:** `200 OK`
- **Response:** `{"status": "healthy", "model_loaded": true}`

### `POST /webhooks/transaction-evaluation`
Ingests real-time transaction event data, validates types via Pydantic, and returns churn risk probabilities.

**Status Codes:**
- `200 OK` — Successful inference evaluation.
- `422 Unprocessable Entity` — Invalid JSON payload structure or value constraint violations.
- `503 Service Unavailable` — ML model artifact is missing or not loaded.

---

## 📄 License

This project is open-source under the MIT License.

---

*Developed by Shiven Siwach | Independent ML Engineer*
