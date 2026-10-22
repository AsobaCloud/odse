"""
Behavioral verification tests for the Durban Feeder Grid Modeling & BESS Dispatch Colab Tutorial.
Verifies BEH-01 through BEH-06 according to the tutorial behavioral specification.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from odse.validator import validate_batch
from odse.adapters.pvlib import odse_to_pvlib, pvlib_to_odse

COLAB_DATA = Path(__file__).resolve().parents[3] / "colab" / "data"

@pytest.fixture(scope="module")
def feeder_data():
    sites = {
        'thokoza': {'pv_mw': 1.2, 'bess_mw': 1.0, 'bess_mwh': 2.0},
        'khanyisa': {'pv_mw': 3.6, 'bess_mw': 2.0, 'bess_mwh': 4.0},
        'simunye': {'pv_mw': 0.75, 'bess_mw': 0.0, 'bess_mwh': 0.0}
    }
    pv_dfs = {}
    grid_dfs = {}
    for s in sites:
        pv_dfs[s] = pd.read_csv(COLAB_DATA / f"{s}_telemetry_6mo.csv.gz", parse_dates=['timestamp'])
        grid_dfs[s] = pd.read_csv(COLAB_DATA / f"{s}_grid_load_6mo.csv.gz", parse_dates=['timestamp'])
    return {'sites': sites, 'pv': pv_dfs, 'grid': grid_dfs}


def test_beh_01_multi_site_odse_batch_validation(feeder_data):
    """BEH-01: Multi-Site ODS-E Batch Validation."""
    thokoza_pv = feeder_data['pv']['thokoza']
    sample_df = thokoza_pv.head(50)
    sample_records = []
    for r in sample_df.itertuples():
        sample_records.append({
            'timestamp': r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp),
            'kWh': float(r.kwh),
            'kW': float(r.power),
            'voltage_ac': float(r.voltage),
            'temperature': float(r.temperature),
            'poa_irradiance': float(r.irradiance),
            'wind_speed_ms': float(r.wind_speed),
            'error_type': str(r.error_type),
            'asset_id': str(r.asset_id),
        })
    res = validate_batch(sample_records)
    assert res.invalid == 0
    assert res.valid == len(sample_records)
    assert len(res.errors) == 0


def test_beh_02_odse_to_pvlib_mapping(feeder_data):
    """BEH-02: ODS-E to pvlib Telemetry Mapping."""
    thokoza_pv = feeder_data['pv']['thokoza']
    inv = thokoza_pv[thokoza_pv['asset_id'] == 'INV-THK-01'].copy()
    inv = inv.rename(columns={'power': 'kW', 'kwh': 'kWh', 'irradiance': 'poa_irradiance'})
    payload = {
        'metadata': {'site_id': 'Thokoza', 'asset_id': 'INV-THK-01', 'rated_kw': 200},
        'telemetry': inv.head(288).to_dict(orient='records')
    }
    pvd, meta = odse_to_pvlib(payload, map_variables=True)
    assert isinstance(pvd.index, pd.DatetimeIndex)
    assert str(pvd.index.tz) == 'UTC'
    assert 'p_mp' in pvd.columns
    assert 'poa_global' in pvd.columns
    assert meta['site_id'] == 'Thokoza'


def test_beh_03_feeder_backfeed_detection(feeder_data):
    """BEH-03: Feeder Backfeed Detection."""
    g = feeder_data['grid']
    total_solar = g['thokoza']['solar_generation_kw'] + g['khanyisa']['solar_generation_kw'] + g['simunye']['solar_generation_kw']
    total_demand = g['thokoza']['building_load_kw'] + g['khanyisa']['building_load_kw'] + g['simunye']['building_load_kw']
    net_unmitigated = total_demand - total_solar

    unmitigated_backfeed = net_unmitigated[net_unmitigated < 0]
    backfeed_hours = len(unmitigated_backfeed) * (5.0 / 60.0)
    assert unmitigated_backfeed.min() < 0
    # Peak backfeed reaches ~ -1.66 MW (-1665 kW)
    assert abs(unmitigated_backfeed.min() - (-1665.1)) < 1.0
    # Total duration is approx 108.8 hours
    assert abs(backfeed_hours - 108.8) < 1.0


def test_beh_04_bess_reverse_flow_mitigation(feeder_data):
    """BEH-04: BESS Coordinated Dispatch & Backfeed Mitigation."""
    g = feeder_data['grid']
    total_solar = g['thokoza']['solar_generation_kw'] + g['khanyisa']['solar_generation_kw'] + g['simunye']['solar_generation_kw']
    total_demand = g['thokoza']['building_load_kw'] + g['khanyisa']['building_load_kw'] + g['simunye']['building_load_kw']
    net_unmitigated = total_demand - total_solar
    total_bess_power = g['thokoza']['bess_power_kw'] + g['khanyisa']['bess_power_kw']
    net_mitigated = net_unmitigated - total_bess_power

    unmitigated_backfeed = net_unmitigated[net_unmitigated < 0]
    mitigated_backfeed = net_mitigated[net_mitigated < 0]

    unmitigated_hours = len(unmitigated_backfeed) * (5.0 / 60.0)
    mitigated_hours = len(mitigated_backfeed) * (5.0 / 60.0)

    # Reduction must be over 80% (mitigated < 20% of unmitigated)
    assert mitigated_hours < 0.20 * unmitigated_hours
    assert (1.0 - (mitigated_hours / unmitigated_hours)) > 0.80


def test_beh_05_economic_tou_tariff_arbitrage(feeder_data):
    """BEH-05: Economic TOU Tariff Arbitrage Audit."""
    g = feeder_data['grid']
    timestamps = g['thokoza']['timestamp']
    timestamps_sast = timestamps.dt.tz_convert('Africa/Johannesburg') if timestamps.dt.tz is not None else timestamps.dt.tz_localize('UTC').dt.tz_convert('Africa/Johannesburg')

    total_solar = g['thokoza']['solar_generation_kw'] + g['khanyisa']['solar_generation_kw'] + g['simunye']['solar_generation_kw']
    total_demand = g['thokoza']['building_load_kw'] + g['khanyisa']['building_load_kw'] + g['simunye']['building_load_kw']
    net_unmitigated = total_demand - total_solar
    total_bess_power = g['thokoza']['bess_power_kw'] + g['khanyisa']['bess_power_kw']
    net_mitigated = net_unmitigated - total_bess_power

    def get_megaflex_rate(dt):
        is_weekday = dt.weekday() < 5
        is_winter = dt.month in [6, 7, 8]
        hour = dt.hour
        if is_weekday:
            if is_winter:
                if (6 <= hour < 9) or (17 <= hour < 19): return 4.95
                elif (9 <= hour < 17) or (19 <= hour < 22): return 1.78
                else: return 0.92
            else:
                if (7 <= hour < 10) or (18 <= hour < 20): return 2.85
                elif (6 <= hour < 7) or (10 <= hour < 18) or (20 <= hour < 22): return 1.45
                else: return 0.78
        else:
            if 12 <= hour < 18: return 1.35 if is_winter else 1.10
            else: return 0.92 if is_winter else 0.78

    tariff_rates = np.array([get_megaflex_rate(dt) for dt in timestamps_sast])
    interval_hours = 5.0 / 60.0
    cost_unmitigated = np.maximum(net_unmitigated, 0) * interval_hours * tariff_rates
    cost_mitigated = np.maximum(net_mitigated, 0) * interval_hours * tariff_rates

    total_savings = cost_unmitigated.sum() - cost_mitigated.sum()
    assert total_savings > 1_000_000.0  # Around R 1.095M savings

    monthly_df = pd.DataFrame({
        'timestamp': timestamps_sast.dt.tz_localize(None),
        'cost_baseline': cost_unmitigated,
        'cost_bess': cost_mitigated,
        'savings': cost_unmitigated - cost_mitigated
    })
    monthly_df['month'] = monthly_df['timestamp'].dt.to_period('M')
    monthly_summary = monthly_df.groupby('month')[['cost_baseline', 'cost_bess', 'savings']].sum()
    assert (monthly_summary['savings'] > 0).all()


def test_beh_06_pvlib_to_odse_roundtrip_export(feeder_data):
    """BEH-06: Standardized ODS-E Interchange Export."""
    g = feeder_data['grid']
    timestamps = g['thokoza']['timestamp']
    total_solar = g['thokoza']['solar_generation_kw'] + g['khanyisa']['solar_generation_kw'] + g['simunye']['solar_generation_kw']
    total_demand = g['thokoza']['building_load_kw'] + g['khanyisa']['building_load_kw'] + g['simunye']['building_load_kw']
    net_mitigated = (total_demand - total_solar) - (g['thokoza']['bess_power_kw'] + g['khanyisa']['bess_power_kw'])

    interval_hours = 5.0 / 60.0
    export_df = pd.DataFrame({
        'p_mp': net_mitigated.values,
        'ac_energy': (np.maximum(net_mitigated, 0) * interval_hours).values,
        'poa_global': total_solar.values
    }, index=pd.DatetimeIndex(timestamps))

    feeder_metadata = {
        'substation_id': 'DBN-11KV-NORTH',
        'feeder_id': 'FDR-IND-04',
        'transformer_kva': 5000,
        'mitigation_strategy': 'BESS_COORDINATED_DISPATCH',
        'currency': 'ZAR'
    }

    odse_export = pvlib_to_odse(
        df=export_df.head(10),
        site_id='Durban-North-11kV-Feeder',
        metadata=feeder_metadata
    )

    assert 'telemetry' in odse_export
    assert len(odse_export['telemetry']) == 10
    assert 'metadata' in odse_export
    assert odse_export['metadata']['substation_id'] == 'DBN-11KV-NORTH'
    sample = odse_export['telemetry'][0]
    assert 'timestamp' in sample
    assert sample['kW'] is not None
    assert sample['kWh'] is not None
