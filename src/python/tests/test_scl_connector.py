import pytest
from pathlib import Path
from odse.connectors.scl import SCLParser, SCLMetadataExtractor

@pytest.fixture
def mock_scd_path():
    # Look for it in examples/data
    return Path(__file__).parents[3] / "examples" / "data" / "mock_template_scada_inverter.scd"

def test_scl_parser_assets(mock_scd_path):
    if not mock_scd_path.exists():
        pytest.skip("Mock SCD file not found")
        
    parser = SCLParser(mock_scd_path)
    assets = parser.extract_assets()
    
    assert len(assets) > 0
    # Check for the expected naming convention (updated to match mock data)
    assert assets[0].asset_id.startswith("solarplant-a")
    assert any(a.ied_name == "TEMPLATE_INV_01" for a in assets)

def test_scl_parser_measurements(mock_scd_path):
    if not mock_scd_path.exists():
        pytest.skip("Mock SCD file not found")
        
    parser = SCLParser(mock_scd_path)
    measurements = parser.extract_measurements(ied_name="TEMPLATE_INV_01")
    
    assert len(measurements) > 0
    # Should have kWh (TotWh) and kW (W) at least
    types = [m.measurement_type for m in measurements]
    assert "TotWh" in types
    assert "W" in types
    
    fields = [m.ods_e_field for m in measurements]
    assert "kWh" in fields
    assert "kW" in fields

def test_scl_metadata_extractor(mock_scd_path):
    if not mock_scd_path.exists():
        pytest.skip("Mock SCD file not found")
        
    extractor = SCLMetadataExtractor(mock_scd_path)
    metadata = extractor.extract_all()
    
    assert "assets" in metadata
    assert "measurement_mappings" in metadata
    assert len(metadata["assets"]) > 0
    assert len(metadata["measurement_mappings"]) > 0
