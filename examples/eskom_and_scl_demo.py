#!/usr/bin/env python3
"""Example: Using SCADA/SCL and Eskom connectors."""

from pathlib import Path
import sys

# Allow running from repo root without installation.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "python"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

def main():
    from odse.connectors.scl import SCLMetadataExtractor
    from odse.transformer import transform

    # 1. SCADA / IEC 61850 SCL Metadata Extraction
    scd_path = ROOT / "examples" / "data" / "mock_template_scada_inverter.scd"
    print(f"--- 1. Extracting metadata from SCL: {scd_path.name} ---")
    
    if scd_path.exists():
        extractor = SCLMetadataExtractor(scd_path)
        metadata = extractor.extract_all()
        
        print(f"Found {len(metadata['assets'])} assets in SCL hierarchy.")
        for asset in metadata['assets'][:2]:
            print(f"  - {asset['asset_id']} ({asset['asset_type']})")
        
        print(f"Found {len(metadata['measurement_mappings'])} measurement mappings.")
        # Print a sample mapping
        if metadata['measurement_mappings']:
            m = metadata['measurement_mappings'][0]
            print(f"  - Mapping: {m['scl_measurement']} -> {m['ods_e_field']}")
    else:
        print("SCL file not found. Skipping.")

    # 2. Eskom Portal Transformation (National Aggregated Data)
    portal_csv = ROOT / "src" / "python" / "tests" / "fixtures" / "eskom_portal_sample.csv"
    print(f"\n--- 2. Transforming Eskom Portal Data: {portal_csv.name} ---")
    
    if portal_csv.exists():
        # Using the "eskom" source alias
        records = transform(portal_csv, source="eskom")
        print(f"Generated {len(records)} ODS-E records from wide-format portal CSV.")
        
        # Group by asset to show long-format conversion
        assets = set(r['asset_id'] for r in records)
        print(f"Metrics extracted: {len(assets)}")
        for aid in sorted(list(assets))[:3]:
            print(f"  - {aid}")
    else:
        print("Eskom Portal sample not found. Skipping.")

    # 3. Eskom AMR Transformation (NRS 049 Meter Data)
    amr_csv = ROOT / "src" / "python" / "tests" / "fixtures" / "eskom_amr_sample.csv"
    print(f"\n--- 3. Transforming Eskom AMR Data: {amr_csv.name} ---")
    
    if amr_csv.exists():
        # Using the "eskom_amr" source alias
        records = transform(amr_csv, source="eskom_amr")
        print(f"Generated {len(records)} ODS-E records from NRS 049 meter data.")
        
        if records:
            sample = records[0]
            print("Sample Record:")
            print(f"  Timestamp: {sample['timestamp']}")
            print(f"  Asset: {sample['asset_id']}")
            print(f"  kWh: {sample['kWh']}")
            print(f"  Billing Status: {sample['billing_status']}")
    else:
        print("Eskom AMR sample not found. Skipping.")

if __name__ == "__main__":
    main()
