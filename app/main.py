import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from app.schemas import WebhookTransactionPayload, ChurnEvaluationResponse

app = FastAPI(
    title="B2B Fintech Real-Time Churn Evaluation Engine",
    description="Event-driven inference microservice for corporate card telemetry and ERP sync health.",
    version="1.0.0"
)

# Load trained model artifact
try:
    model = joblib.load("model/churn_model.pkl")
except Exception:
    model = None

@app.get("/")
def root():
    return {
        "service": "B2B Fintech Real-Time Churn Evaluation Engine",
        "status": "online",
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "model_loaded": model is not None}

@app.post("/webhooks/transaction-evaluation", response_model=ChurnEvaluationResponse)
def evaluate_transaction_webhook(payload: WebhookTransactionPayload):
    if not model:
        raise HTTPException(status_code=503, detail="Model artifact not found. Please train model first.")
    
    features = np.array([[
        payload.weekly_transaction_count,
        payload.receipt_upload_ratio,
        payload.erp_sync_errors,
        payload.days_since_last_active
    ]])
    
    churn_prob = float(model.predict_proba(features)[0][1])
    
    if churn_prob >= 0.70:
        risk_level = "CRITICAL"
        action_required = True
        summary = "High churn signal: Severe drop in transaction velocity and sync failures."
    elif churn_prob >= 0.40:
        risk_level = "ELEVATED"
        action_required = False
        summary = "Moderate risk: Monitor receipt compliance and card usage over the next 7 days."
    else:
        risk_level = "LOW"
        action_required = False
        summary = "Healthy customer engagement."

    return ChurnEvaluationResponse(
        sme_id=payload.sme_id,
        transaction_id=payload.transaction_id,
        churn_risk_score=round(churn_prob, 4),
        risk_level=risk_level,
        action_required=action_required,
        summary=summary
    )