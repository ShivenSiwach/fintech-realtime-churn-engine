# 🚀 B2B Fintech Real-Time Churn Engine
 
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/ShivenSiwach/fintech-realtime-churn-engine)
[![CI](https://github.com/ShivenSiwach/fintech-realtime-churn-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/ShivenSiwach/fintech-realtime-churn-engine/actions/workflows/ci.yml)
![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green.svg)
 
An event-driven machine learning inference microservice designed to evaluate SME churn risk and accounting ERP sync health in real-time from corporate card transaction telemetry.
 
> **Why this project exists:** I built this as a targeted concept piece for **[Mynt](https://www.mynt.com/en)**, a Stockholm-based B2B corporate card and expense platform. Rather than a generic churn-prediction demo, every design choice here — the feature set (card velocity, receipt compliance, ERP sync health), the Fortnox/Visma/Xero references, the SEK-denominated payloads — is modeled on Mynt's actual product surface. It's a working demonstration of how I'd approach real-time churn risk scoring for their SME customer base, and an open invitation to talk.
 
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
**Current scaling limitation:** this is a single-instance service with the model loaded in-memory on startup — there's no request queue, batching, or horizontal scaling yet. That's fine for a demo and for moderate webhook volume behind a load balancer with multiple replicas, but a production deployment at Mynt's actual transaction volume would need either autoscaled replicas behind a shared model store, or a batched inference layer, depending on real traffic patterns.
 
---
 
## 📈 3. Model & Data
 
[#-3-model--data](#-3-model--data)
 
**⚠️ Synthetic data disclosure:** this model is trained on synthetically generated telemetry (`data/generate_mock_data.py`), not real Mynt or customer data. It exists to demonstrate the inference architecture and feature engineering approach — not to make production churn claims. The feature relationships (declining transaction velocity, dropping receipt compliance, rising ERP sync errors → churn) are hand-modeled from the domain narrative above, then a Random Forest is trained to recover that signal.
 
**Held-out test performance** (80/20 split, stratified, `random_state=42` — reproducible via `python data/evaluate_model.py`):
 
| Metric | Score |
| --- | --- |
| Precision (churned) | 0.885 |
| Recall (churned) | 0.622 |
| F1 (churned) | 0.730 |
| ROC-AUC | 0.990 |
 
Base rate: ~7.4% of accounts churn in the synthetic set, so this is a class-imbalanced problem — precision/recall on the minority class matter more than raw accuracy (which is a misleading 97%).
 
**Risk band calibration** — checking whether the `CRITICAL` / `ELEVATED` / `LOW` thresholds in the Risk Evaluation Engine actually track real risk on the test set:
 
| Band | Threshold | Accounts | Actual churn rate in band |
| --- | --- | --- | --- |
| CRITICAL | score ≥ 0.70 | 37 | 94.6% |
| ELEVATED | 0.40 ≤ score < 0.70 | 27 | 70.4% |
| LOW | score < 0.40 | 936 | 2.1% |
 
The bands are well-separated on synthetic data, which validates the threshold design — but recall of 0.62 means roughly a third of true churners are being under-scored. On real data, that recall gap is where feature work should focus next.
 
---
 
## 📂 4. Project Structure
 
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
 
## 📊 5. Telemetry Features & Data Dictionary
 
| Feature Name | Type | Description | Churn Impact |
|---|---|---|---|
| `weekly_transaction_count` | `Integer` | Total corporate card transactions in the trailing 7 days. | Inverse: Low swipe volume indicates disengagement. |
| `receipt_upload_ratio` | `Float (0.0 - 1.0)` | Ratio of settled expenses with verified receipt images. | Inverse: Drop below 0.50 indicates workflow abandonment. |
| `erp_sync_errors` | `Integer` | Unresolved sync errors with external accounting software. | Direct: Higher sync failures correlate with platform frustration. |
| `days_since_last_active` | `Float` | Days elapsed since an admin/cardholder accessed the app. | Direct: Inactivity is a primary leading indicator of churn. |
 
---
 
## 🧪 6. Live Interactive Demo (No Setup Required)
 
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
 
## 💻 7. Local Setup & Container Deployment
 
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
 
## 🔒 8. API Specification
 
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
**`200 OK` example:**
```json
{
  "sme_id": "sme_stockholm_041",
  "transaction_id": "tx_se_88219",
  "churn_risk_score": 0.974,
  "risk_level": "CRITICAL",
  "action_required": true,
  "summary": "High churn signal: Severe drop in transaction velocity and sync failures."
}
```
 
**`422 Unprocessable Entity` example** — missing required field (`weekly_transaction_count`):
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "weekly_transaction_count"],
      "msg": "Field required"
    }
  ]
}
```
 
**`422 Unprocessable Entity` example** — value outside declared bounds (`receipt_upload_ratio: 1.5`, but schema requires `≤ 1.0`):
```json
{
  "detail": [
    {
      "type": "less_than_equal",
      "loc": ["body", "receipt_upload_ratio"],
      "msg": "Input should be less than or equal to 1"
    }
  ]
}
```
 
**`503 Service Unavailable` example** — model artifact missing at boot:
```json
{
  "detail": "Model artifact not found. Please train model first."
}
```
 
### Latency
 
Benchmarked in-process (FastAPI `TestClient`, 200 sequential requests, single instance, warm model already loaded — no network hop):
 
| Percentile | Latency |
| --- | --- |
| Mean | 4.4ms |
| Median | 4.3ms |
| p95 | 5.0ms |
| p99 | 5.8ms |
 
This measures inference + validation overhead only, not real network latency — over an actual HTTP connection (webhook → load balancer → service), expect single-digit milliseconds added on top depending on network path. The **<15ms** claim in the intro holds comfortably at this model size, but hasn't been benchmarked yet under concurrent load or with a real network hop, both of which belong in the Roadmap once this moves past demo stage.
 
---
 
## 🧪 9. Testing
 
[#-9-testing](#-9-testing)
 
The webhook endpoint is covered by `pytest` cases for valid payloads, schema-validation failures, and the model-unavailable path. Every push and pull request to `main` runs the full suite via GitHub Actions (`.github/workflows/ci.yml`) — model generation, evaluation, and tests, in that order.
 
```
# Install dev dependencies (includes a compatible httpx pin — see requirements-dev.txt)
pip install -r requirements-dev.txt
 
# Ensure a model artifact exists
python data/generate_mock_data.py
 
# Run the suite
pytest tests/ -v
```
 
---
 
## 🗺️ 10. Roadmap
 
[#-10-roadmap](#-10-roadmap)
 
This service currently ships a single, statically trained model artifact — good enough to demonstrate the inference architecture, but not how you'd want to run churn scoring in production. The natural next step is applying the same pattern from my Automated Continuous Training (CT) pipeline project to this service:
 
- **Drift detection**: a KS-test module comparing incoming `weekly_transaction_count` / `receipt_upload_ratio` / `erp_sync_errors` distributions against the training baseline, flagging when live SME behavior has drifted from what the model was trained on.
- **Automated retraining trigger**: a branch/gate step (Airflow or GitHub Actions) that kicks off retraining only when drift crosses a threshold, rather than on a blind schedule.
- **Blue/Green redeployment**: swap traffic to a newly retrained model with zero downtime once it clears a promotion gate (e.g. an MLflow-tracked comparison against the currently serving model), rather than manually replacing `model/churn_model.pkl`.
- **Real feature validation**: replacing the synthetic training data (see [Model & Data](#-3-model--data)) with real telemetry once available, and re-running the eval script to confirm the risk-band calibration still holds.
---
 
## 📄 License
 
This project is open-source under the MIT License.
 
---
 
*Built by Shiven Siwach — Final-year M.Sc. Data Science & Machine Learning student.*
*Open to connecting: [GitHub](https://github.com/ShivenSiwach) · [LinkedIn](https://linkedin.com/in/shivensiwach)*
