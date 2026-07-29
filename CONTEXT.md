# Stock Analyzer App - Domain Glossary (CONTEXT.md)

## Bounded Context: Cron Scheduler & Admin Setup

### Terms

* **Cron Scheduler Worker**: Background process running `2_cron_scheduler/scheduler.py` inside the `stock_scheduler` container, responsible for triggering sequential stock report generation.
* **Cron Configuration (`cron_config`)**: SQLite database record containing active schedule parameters (schedule time, timezone, active days, misfire grace window, delay between tickers, enabled state).
* **Misfire Grace Window**: Maximum allowable time delta (in minutes) between scheduled trigger time and actual execution start time. If the host machine wakes up within this window, missed jobs are executed immediately.
* **Single-Run Guard (`is_running` Lock)**: Mechanism preventing multiple concurrent stock analysis batch runs from executing simultaneously.
* **Watchlist**: Collection of active tickers (and target language preferences) queued for daily automated analysis.
