# ADR 0002: Unified JSON Locales for Web Server UI & Core Report Builder

## Context & Decision
Initially, web application UI translations (`UI_I18N`) were embedded as Python dictionaries in `3_web_server/main.py`, while report translations were embedded in `1_core_builder/html_compiler.py`.

We decided to standardize both components to use external JSON localization catalogs (`locales/{lang}.json`):
1. **Core Report Builder**: `1_core_builder/locales/tr.json` and `1_core_builder/locales/en.json`
2. **Web Server Application**: `3_web_server/locales/tr.json` and `3_web_server/locales/en.json`

## Rationale & Consequences
- **Decoupled Translations**: Non-developer translators can edit JSON files without modifying Python application code or HTML templates.
- **Unified i18n Standard**: Both backend APIs and HTML dashboard compilers follow the exact same catalog structure (`locales/{lang}.json`).
- **Ease of Maintenance**: Adding a new language across the entire platform requires creating corresponding `{lang}.json` files in the two locales directories.
