import pytest
from pathlib import Path
from odse.transformer import EskomPortalTransformer, EskomAMRTransformer

@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"

def test_eskom_portal_transformer(fixtures_dir):
    transformer = EskomPortalTransformer()
    sample_path = fixtures_dir / "eskom_portal_sample.csv"
    
    records = transformer.transform(sample_path)
    
    # Each row has ~10 metrics (thermal, nuclear, etc.)
    # 2 rows * 10 metrics = 20 records
    assert len(records) >= 20
    
    # Check a specific record
    thermal_records = [r for r in records if r["asset_id"] == "za-eskom:generation:thermal"]
    assert len(thermal_records) == 2
    assert thermal_records[0]["timestamp"] == "2026-05-31T06:00:00Z"
    assert thermal_records[0]["kW"] == 20000.0
    assert thermal_records[0]["kWh"] == 20000.0 * 0.5  # 30 min interval

def test_eskom_amr_transformer(fixtures_dir):
    transformer = EskomAMRTransformer()
    sample_path = fixtures_dir / "eskom_amr_sample.csv"
    
    records = transformer.transform(sample_path)
    
    assert len(records) == 2
    
    # Row 1
    rec1 = records[0]
    assert rec1["asset_id"] == "za-eskom:meter:9857665714F1"
    assert rec1["billing_status"] == "metered"
    assert rec1["kWh_import"] == 150.5 * 0.5
    assert rec1["kWh_export"] == 10.2 * 0.5
    assert rec1["kWh"] == (150.5 - 10.2) * 0.5
    
    # Row 2
    rec2 = records[1]
    assert rec2["billing_status"] == "estimated"
    assert rec2["timestamp"] == "2026-05-31T06:30:00Z"
