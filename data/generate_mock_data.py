import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

def generate_fintech_churn_data(n_samples=5000):
    np.random.seed(42)
    sme_ids = [f"sme_{i:04d}" for i in range(n_samples)]
    
    # Behavioral features for B2B card telemetry
    weekly_tx_count = np.random.poisson(lam=25, size=n_samples)
    receipt_upload_ratio = np.clip(np.random.normal(loc=0.85, scale=0.15, size=n_samples), 0, 1)
    erp_sync_errors = np.random.poisson(lam=1.2, size=n_samples)
    days_since_last_active = np.random.exponential(scale=4, size=n_samples)
    
    # Logit calculation for churn risk
    churn_logits = (
        - 0.08 * weekly_tx_count
        - 3.5 * receipt_upload_ratio
        + 0.9 * erp_sync_errors
        + 0.3 * days_since_last_active
        + np.random.normal(0, 0.5, n_samples)
    )
    churn_prob = 1 / (1 + np.exp(-churn_logits))
    churned = (churn_prob > 0.5).astype(int)
    
    df = pd.DataFrame({
        "sme_id": sme_ids,
        "weekly_transaction_count": weekly_tx_count,
        "receipt_upload_ratio": receipt_upload_ratio,
        "erp_sync_errors": erp_sync_errors,
        "days_since_last_active": days_since_last_active,
        "churn": churned
    })
    return df

if __name__ == "__main__":
    os.makedirs("model", exist_ok=True)
    df = generate_fintech_churn_data()
    X = df[["weekly_transaction_count", "receipt_upload_ratio", "erp_sync_errors", "days_since_last_active"]]
    y = df["churn"]
    
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(X, y)
    
    joblib.dump(model, "model/churn_model.pkl")
    print("✓ Model trained successfully and saved to model/churn_model.pkl")