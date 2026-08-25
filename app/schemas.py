from pydantic import BaseModel, Field

class WebhookTransactionPayload(BaseModel):
    transaction_id: str
    sme_id: str
    amount_sek: float
    merchant_category: str
    weekly_transaction_count: int = Field(..., ge=0, description="Card swipes in the past 7 days")
    receipt_upload_ratio: float = Field(..., ge=0.0, le=1.0, description="Ratio of expenses with uploaded receipts")
    erp_sync_errors: int = Field(..., ge=0, description="Unresolved accounting sync errors")
    days_since_last_active: float = Field(..., ge=0.0, description="Days since last mobile app or dashboard login")

class ChurnEvaluationResponse(BaseModel):
    sme_id: str
    transaction_id: str
    churn_risk_score: float
    risk_level: str
    action_required: bool
    summary: str