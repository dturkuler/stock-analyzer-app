# ADR 0001: Template-Based Multi-Lingual Report Architecture

## Context & Decision
We needed to support 100% full multi-lingual report generation (English and Turkish) without duplicating HTML layout and JavaScript chart logic across separate template files per language. We decided to maintain a single HTML master template (`1_core_builder/templates/report_template.html`) coupled with dedicated JSON localization catalogs (`locales/tr.json`, `locales/en.json`).

## Rationale & Consequences
- **Single Source of Truth**: Layout modifications, CSS theme tokens, Chart.js logic, and interactive Reverse DCF sliders are maintained in one single Jinja2 master template (`1_core_builder/templates/report_template.html.j2`).
- **Jinja2 Filters**: Locale-aware Jinja2 filters (`fmt_curr`, `fmt_pct`, `fmt_num`) format all currency and financial metrics automatically based on target language.
- **Zero Drift**: Eliminates the risk of English and Turkish report UIs drifting out of sync.
- **Scalability**: Adding a new language (e.g., German/Spanish) only requires creating a new JSON translation catalog (`locales/{lang}.json`) without modifying HTML/CSS structure.
