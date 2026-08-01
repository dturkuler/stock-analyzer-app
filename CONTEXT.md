# Stock Analyzer App - Domain Glossary (CONTEXT.md) (v2.3.0)

## Bounded Context: System Architecture & Engine Terminology

### Terms

* **Cron Scheduler Worker**: Background process running `2_cron_scheduler/scheduler.py` inside the `stock_scheduler` container, responsible for triggering sequential stock report generation.
* **Cron Configuration (`cron_config`)**: SQLite database record containing active schedule parameters (schedule time, timezone, active days, misfire grace window, delay between tickers, enabled state).
* **Misfire Grace Window**: Maximum allowable time delta (in minutes) between scheduled trigger time and actual execution start time. If the host machine wakes up within this window, missed jobs are executed immediately.
* **Single-Run Guard (`is_running` Lock)**: Mechanism preventing multiple concurrent stock analysis batch runs from executing simultaneously.
* **Watchlist**: Collection of active tickers (and target language preferences) queued for daily automated analysis in `storage/app.db`.
* **2-Stage LLM Commentary Pipeline**: 2-stage prompt architecture (Stage 1 Quant Audit, Stage 2 Retail Blog Briefing) with language enforcers and Stage 1 retries.
* **GFX Pre-rendered Static SVG Engine**: SVG line chart pre-rendering component in `1_core_builder/html_compiler.py` generating inline vector graphics for historical trends.
* **Schema Migration Helper (`db_schema.py`)**: Automatic database table and column migration manager.
* **Strict Error Logging (`errors.log`)**: Log file capturing all sourcing failures and exception tracebacks across the builder and server components.
