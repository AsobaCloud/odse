# Alarm Frequency Profile Computation (SEP-038)

Status: Draft
Last updated: 2026-02-25

## Purpose

The alarm frequency profile is a **derived** enrichment record — it does not come directly from any single source system. It is computed by joining SCADA alarm logs with ERP maintenance history and equipment identity mappings to produce per-equipment, per-alarm analytics that answer:

1. **"Is alarm frequency accelerating?"** — via `escalation_rate` comparing recent vs longer-term occurrence rates
2. **"What is the maintenance history for this alarm?"** — via `prior_wo_count_same_alarm` and `prior_resolution`
3. **"How often does this alarm fire?"** — via rolling window counts (`count_7d`, `count_30d`, `count_90d`) and `mean_time_between_alarms_hours`

These analytics are the foundation for the Globeleq use cases: trending event frequency, identifying cascade effects, and linking spare parts consumption to alarm patterns.

## Inputs

| Input | Source | Schema |
|-------|--------|--------|
| Alarm log | SCADA or monitoring system | Vendor-specific (raw alarm events with timestamp, equipment ID, alarm code) |
| Equipment ID map | ODS-E enrichment | `equipment-id-map.json` |
| Maintenance history | ERP via transform | `maintenance-history.json` |
| Failure taxonomy | ERP via transform | `failure-taxonomy.json` |

### Alarm Log Requirements

The raw alarm log must provide at minimum:

- **timestamp** — when the alarm occurred (ISO 8601 datetime)
- **source_equipment_id** — native equipment identifier in the SCADA/monitoring system
- **alarm_code** — alarm identifier (vendor-specific string)

Alarm logs are not standardized by ODS-E because alarm code vocabularies are vendor-specific and site-specific. The computation consumes them as-is and maps equipment IDs via `equipment-id-map.json`.

## Equipment ID Resolution

Before any computation, raw alarm log entries must be resolved to canonical ODS-E equipment IDs:

1. Look up `source_equipment_id` in `equipment-id-map.json` where `sources[].system` matches the SCADA system name and `sources[].type = "scada"` or `"monitoring"`
2. The matching entry's `equipment_id` becomes the canonical ID used in all downstream joins
3. Alarm entries that cannot be resolved are logged as warnings and excluded from the profile

This is the same resolution mechanism used by the ERP transforms (e.g., IFS Cloud maps `MchCode` via `sources[].type = "erp"`).

## Alarm-to-Failure Mapping

To link SCADA alarms to ERP failure codes for the `prior_wo_count_same_alarm` and `prior_resolution` fields, a deployment-specific mapping is required:

| SCADA alarm_code | ERP failure_code |
|------------------|-----------------|
| (site-specific)  | (site-specific) |

This mapping is analogous to the equipment ID map — it bridges vocabulary differences between SCADA alarm taxonomies and ERP failure taxonomies. It must be provided by the site operator or derived from historical co-occurrence analysis.

When no mapping exists for an alarm code, `prior_wo_count_same_alarm` defaults to `0` and `prior_resolution` defaults to `"none"`.

## Window Calculations

All window calculations use a **trailing window** anchored at the computation timestamp.

### count_7d, count_30d, count_90d

For a given `(equipment_id, alarm_code)` pair at computation time `T`:

```
count_Nd = COUNT(alarm_events)
  WHERE equipment_id = {equipment_id}
    AND alarm_code = {alarm_code}
    AND timestamp >= T - N days
    AND timestamp < T
```

### mean_time_between_alarms_hours

```
mtba = AVG(time_delta)
  WHERE time_delta = alarm_events[i+1].timestamp - alarm_events[i].timestamp
    FOR consecutive alarm events on the same (equipment_id, alarm_code)
    WITHIN the 90-day window
```

If fewer than 2 alarm events exist in the 90-day window, `mean_time_between_alarms_hours` is omitted from the output.

### escalation_rate

Compares the weekly alarm rate in the recent 7-day window against the longer-term 30-day baseline:

```
weekly_rate_7d  = count_7d / 1       (already a 1-week window)
weekly_rate_30d = count_30d / (30/7) (normalize 30-day count to weekly rate)

escalation_rate = weekly_rate_7d / weekly_rate_30d
```

Special cases:
- If `count_30d = 0`: `escalation_rate` is omitted (no baseline to compare against)
- If `count_7d = 0` and `count_30d > 0`: `escalation_rate = 0.0` (alarm has stopped)
- Values `> 1.0` indicate accelerating frequency; values `< 1.0` indicate decelerating frequency

### prior_wo_count_same_alarm

```
prior_wo_count_same_alarm = COUNT(work_orders)
  WHERE work_orders.equipment_id = {equipment_id}
    AND work_orders.failure_code = alarm_to_failure_map[{alarm_code}]
```

Counts all historical work orders (no time window restriction) to capture the full maintenance history for this alarm pattern.

### prior_resolution

```
prior_resolution = CASE
  WHEN no matching work orders THEN "none"
  WHEN latest_wo.wo_status = "closed" AND recurrence_in_30d = false THEN "closed_resolved"
  WHEN latest_wo.wo_status = "closed" AND recurrence_in_30d = true  THEN "recurring"
  WHEN latest_wo.wo_status IN ("open", "in_progress")              THEN "closed_deferred"
END
```

Where `latest_wo` is the most recent work order by `completed_date` (or `reported_date` if not yet completed), and `recurrence_in_30d` checks whether the same alarm fired again within 30 days after the work order's `completed_date`.

## Refresh Cadence

The alarm frequency profile should be recomputed:

- **Every 4 hours** during operational hours — aligns with the maintenance history extraction cadence from ERP transforms
- **On demand** when a new alarm burst is detected (optional optimization)

The profile is a snapshot at computation time. Historical profiles may be retained for trend analysis but are not required by the schema.

## Output Schema

Each computation produces one record per unique `(equipment_id, alarm_code)` pair that had at least one alarm event in the 90-day window. The output must conform to `schemas/alarm-frequency-profile.json`.

### Example Output

```json
{
  "equipment_id": "SITE01-INV-003",
  "alarm_code": "GRID_FAULT_UV",
  "source_equipment_id": "INV-003-SCADA",
  "count_7d": 12,
  "count_30d": 18,
  "count_90d": 25,
  "mean_time_between_alarms_hours": 86.4,
  "escalation_rate": 2.86,
  "prior_wo_count_same_alarm": 3,
  "prior_resolution": "recurring"
}
```

In this example, `escalation_rate = 12 / (18 / 4.286) = 12 / 4.2 = 2.86`, indicating the alarm is firing nearly 3x faster in the last week compared to the 30-day baseline.

## Related Documents

- [Equipment ID Map Schema](../schemas/equipment-id-map.json) — canonical equipment identity resolution
- [Maintenance History Schema](../schemas/maintenance-history.json) — work order records joined for prior resolution
- [Failure Taxonomy Schema](../schemas/failure-taxonomy.json) — failure code reference for alarm-to-failure mapping
- [Alarm Frequency Profile Schema](../schemas/alarm-frequency-profile.json) — output schema for this computation
- [IFS Cloud Transform](../erp-transforms/ifs-cloud.yaml) — ERP extraction that feeds maintenance history and failure taxonomy inputs
