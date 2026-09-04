"""
Test suite for the churn evaluation webhook.
 
Run with: pytest tests/ -v
Requires model/churn_model.pkl to exist (run `python data/generate_mock_data.py` first,
same as the Dockerfile does at build time).
"""
import pytest
from fastapi.testclient import TestClient
 
import app.main as main_module
from app.main import app
 
client = TestClient(app)
 
VALID_PAYLOAD = {
    "transaction_id": "tx_se_88219",
    "sme_id": "sme_stockholm_041",
    "amount_sek": 4500.0,
    "merchant_category": "Cloud Services",
    "weekly_transaction_count": 2,
    "receipt_upload_ratio": 0.15,
    "erp_sync_errors": 6,
    "days_since_last_active": 14.0,
}
 
 
class TestHealthEndpoint:
    def test_health_reports_model_loaded(self):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["model_loaded"] is True
 
    def test_health_reports_model_not_loaded(self, monkeypatch):
        # Simulate a deployment where the model artifact failed to load.
        monkeypatch.setattr(main_module, "model", None)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["model_loaded"] is False
 
 
class TestWebhookValidPayload:
    def test_returns_200_with_expected_shape(self):
        response = client.post("/webhooks/transaction-evaluation", json=VALID_PAYLOAD)
        assert response.status_code == 200
        body = response.json()
 
        for field in ("sme_id", "transaction_id", "churn_risk_score", "risk_level", "action_required", "summary"):
            assert field in body
 
        assert body["sme_id"] == VALID_PAYLOAD["sme_id"]
        assert body["transaction_id"] == VALID_PAYLOAD["transaction_id"]
        assert 0.0 <= body["churn_risk_score"] <= 1.0
        assert body["risk_level"] in ("LOW", "ELEVATED", "CRITICAL")
        assert isinstance(body["action_required"], bool)
 
    def test_high_risk_payload_flags_action_required(self):
        # Deliberately distressed account: low tx count, low receipts, many sync errors, long inactivity.
        response = client.post("/webhooks/transaction-evaluation", json=VALID_PAYLOAD)
        body = response.json()
        if body["risk_level"] == "CRITICAL":
            assert body["action_required"] is True
 
    def test_healthy_account_scores_low(self):
        healthy_payload = {
            **VALID_PAYLOAD,
            "weekly_transaction_count": 45,
            "receipt_upload_ratio": 0.98,
            "erp_sync_errors": 0,
            "days_since_last_active": 0.5,
        }
        response = client.post("/webhooks/transaction-evaluation", json=healthy_payload)
        assert response.status_code == 200
        assert response.json()["risk_level"] == "LOW"
 
 
class TestWebhookMalformedPayload:
    def test_missing_required_field_returns_422(self):
        bad_payload = VALID_PAYLOAD.copy()
        del bad_payload["weekly_transaction_count"]
        response = client.post("/webhooks/transaction-evaluation", json=bad_payload)
        assert response.status_code == 422
 
    def test_wrong_type_returns_422(self):
        bad_payload = {**VALID_PAYLOAD, "weekly_transaction_count": "not_a_number"}
        response = client.post("/webhooks/transaction-evaluation", json=bad_payload)
        assert response.status_code == 422
 
    def test_negative_value_violates_constraint_returns_422(self):
        # erp_sync_errors has ge=0 in the schema
        bad_payload = {**VALID_PAYLOAD, "erp_sync_errors": -3}
        response = client.post("/webhooks/transaction-evaluation", json=bad_payload)
        assert response.status_code == 422
 
    def test_receipt_ratio_out_of_bounds_returns_422(self):
        # receipt_upload_ratio has le=1.0 in the schema
        bad_payload = {**VALID_PAYLOAD, "receipt_upload_ratio": 1.5}
        response = client.post("/webhooks/transaction-evaluation", json=bad_payload)
        assert response.status_code == 422
 
    def test_empty_body_returns_422(self):
        response = client.post("/webhooks/transaction-evaluation", json={})
        assert response.status_code == 422
 
 
class TestWebhookModelUnavailable:
    def test_returns_503_when_model_not_loaded(self, monkeypatch):
        monkeypatch.setattr(main_module, "model", None)
        response = client.post("/webhooks/transaction-evaluation", json=VALID_PAYLOAD)
        assert response.status_code == 503
        assert "model" in response.json()["detail"].lower()
 
