import os
import io
import json
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Sample CSV data for testing
def sample_csv():
    return io.BytesIO(b"feature1,feature2,feature3\n1,2,3\n4,5,6\n")

def test_predict_with_external_data():
    # Prepare form data with mock external data
    request_data = {
        "model_id": "11111111",
        "other_param": "value",  # Add other required fields as needed
        "google_analytics": {
            "sessions": 1200,
            "bounce_rate": 0.45,
            "avg_session_duration": 180
        },
        "facebook_ads": {
            "impressions": 5000,
            "clicks": 300,
            "spend": 150.75
        },
        "google_ads": {
            "impressions": 8000,
            "clicks": 400,
            "spend": 200.50
        }
    }
    response = client.post(
        "/predict-with-external-data",
        files={"file": ("test.csv", sample_csv(), "text/csv")},
        data={"request": json.dumps(request_data)}
    )
    assert response.status_code == 200
    # Optionally, check response content structure
    # assert "prediction" in response.json()

@pytest.mark.asyncio
def test_merge_external_data(monkeypatch):
    # Sample main df
    df = pd.DataFrame({
        'date': pd.date_range('2025-07-01', periods=3),
        'value': [100, 200, 300]
    })

    # Sample external data simulating Google Analytics, Facebook Ads, Google Ads
    external_df = pd.DataFrame({
        'date': pd.date_range('2025-07-01', periods=3),
        'ga4_users': [10, 20, 30],
        'fb_ads_spend': [5, 10, 15],
        'google_ads_clicks': [50, 60, 70]
    })

    # Mock request data
    class ReqData:
        use_external_data = True
        start_date = '2025-07-01'
        end_date = '2025-07-03'
        data_sources = ['ga4', 'facebook_ads', 'google_ads']
        merge_on = 'date'

    req_data = ReqData()

    # Mock data_integrator
    mock_data_integrator = AsyncMock()
    mock_data_integrator.fetch_specific_data.return_value = external_df

    # Patch pd.to_datetime to ensure correct types
    monkeypatch.setattr(pd, 'to_datetime', pd.to_datetime)

    # Simulate the merge logic
    merge_col = req_data.merge_on if req_data.merge_on else 'date'
    numeric_cols = external_df.select_dtypes(include=['number']).columns
    external_agg = external_df.groupby(merge_col)[numeric_cols].sum().reset_index()
    df[merge_col] = pd.to_datetime(df[merge_col])
    external_agg[merge_col] = pd.to_datetime(external_agg[merge_col])
    merged_df = df.merge(external_agg, on=merge_col, how='left', suffixes=('', '_external'))

    # Assert merged columns exist
    assert 'ga4_users' in merged_df.columns
    assert 'fb_ads_spend' in merged_df.columns
    assert 'google_ads_clicks' in merged_df.columns
    assert merged_df.shape[0] == 3
    assert merged_df['ga4_users'].iloc[0] == 10
    assert merged_df['fb_ads_spend'].iloc[1] == 10
    assert merged_df['google_ads_clicks'].iloc[2] == 70
