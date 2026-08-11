
## v1.5.0
- **CRITICAL FIX**: Re-engineered historical statistics injection to automatically fetch and accumulate the lifetime total from Home Assistant's database. This permanently eliminates the daily negative usage spikes in the Energy Dashboard caused by midnight resets.
