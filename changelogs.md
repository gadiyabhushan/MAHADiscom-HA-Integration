
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
