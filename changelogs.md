
## v2.1.4
- **STRICT MONOTONIC NON-DECREASING GUARD**:
  - Implemented monotonic upper bounds (`max_sums` and non-decreasing `day_totals`) in the statistics manager.
  - Guarantees historical sensor states and daily totals NEVER decrease even if Mahavitran API temporarily returns partial hourly payloads during server processing.
  - Prevents false meter reset triggers, state drops, and negative import calculations.

## v2.1.3
- **FIXED RESET SPIKES AND DEPRECATION WARNINGS**:
  - Removed raw `current_reading` fallback from historical dashboard sensors, preventing state reset spikes during API glitches.
  - Retain the last computed sums when the API fails to return daily hourly data.
  - Specified `unit_class="energy"` in statistic metadata to fix the HA 2026.11 deprecation warning.

## v2.1.2
- **FIXED 4-HOURLY SPIKES**:
  - Aligned injected UTC timestamps to the top of the hour, resolving the Home Assistant `Invalid timestamp` injection error.
  - Dynamically look up active entity IDs from Home Assistant's entity registry, resolving mismatches when sensors are customized/renamed in the UI (e.g. adding location prefixes like "Parking").
  - Fixed database warnings by explicitly specifying `mean_type=StatisticMeanType.NONE` for metadata.

## v2.1.1
- **CRITICAL FIX**: Fixed AttributeError on startup by restoring the missing `async_initialize_metadata` method inside the statistics manager.

## v2.1.0
- **COMPLETE STABILITY REWRITE**:
  - Restored `Mahavitran Import Historical (Dashboard)` and `Mahavitran Export Historical (Dashboard)` as live, active Home Assistant sensors seeded with lifetime cumulative sums.
  - Fixed "Unavailable" sensor state in Device card.
  - Sensors now appear in the Energy Dashboard dropdown without searching for external statistics.
  - Backdated hourly statistics use lifetime monotonic sums to ensure zero negative spikes, zero midnight drops, and perfect hourly breakdown.

## v2.0.0
- **MAJOR ARCHITECTURAL REWRITE (Permanent Fix for Energy Dashboard)**:
  - Migrated to native Home Assistant **External Statistics** (`mahavitran:import_{consumer_no}` and `mahavitran:export_{consumer_no}`).
  - Removed dummy entity sensors whose 0.0 state was conflicting with Home Assistant's internal recorder daemon.
  - Added multi-day fetching (synchronizes both yesterday and today's hourly records on every cycle).
  - Implemented persistent monotonic prefix sums via `MahavitranStatisticsManager` to guarantee strictly non-decreasing cumulative statistics with zero negative spikes, zero midnight drops, and exact hour-by-hour consumption.

## v1.5.0
- **CRITICAL FIX**: Re-engineered historical statistics injection to automatically fetch and accumulate the lifetime total from Home Assistant's database. This permanently eliminates the daily negative usage spikes in the Energy Dashboard caused by midnight resets.
