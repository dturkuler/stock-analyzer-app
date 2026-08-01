# 📊 Developer Guide: Adding a New Report Tab/Module (v2.3.0)

This guide documents how to add a brand new module or analysis tab to the interactive master research dashboard.

---

## 🛠️ Step-by-Step Procedure

### 1. Add Navigation Item
In `1_core_builder/html_compiler.py`, locate the `<aside class="sidebar">` navigation list and insert a new `nav-item`:

```html
<li class="nav-item" onclick="switchTab('newmodule')" data-i18n="tab_newmodule">
  {"⚡ 14. New Custom Module" if is_en else "⚡ 14. Yeni Özel Modül"}
</li>
```

### 2. Add Tab Pane Container
Inside `<main class="main-content">`, create a matching tab container div:

```html
<!-- TAB 14: NEW CUSTOM MODULE -->
<div id="newmodule" class="tab-pane">
  <div class="investor-guide-box">
    <div class="guide-title">
      {"💡 HOW TO READ NEW CUSTOM MODULE" if is_en else "💡 YENİ ÖZEL MODÜL NASIL YORUMLANIR?"}
    </div>
    <div class="guide-text">
      {"Detailed investor tips and quantitative explanations." if is_en else "Detaylı yatırımcı rehberi ve nicel açıklamalar."}
    </div>
  </div>

  <div class="card">
    <h3 class="card-title">{"⚡ New Custom Module Title" if is_en else "⚡ Yeni Özel Modül Başlığı"}</h3>
    <!-- Insert module table, cards, or pre-rendered GFX SVG chart here -->
  </div>
</div>
```

### 3. Add i18n Translation Keys
Add matching keys to `1_core_builder/locales/en.json` and `1_core_builder/locales/tr.json`:

```json
"tab_newmodule": "⚡ 14. New Custom Module"
```

### 4. Verify & Build
Generate a test report locally or inside Docker container:

```bash
# Local CLI generation
python3 1_core_builder/generate_report.py AAPL --lang EN

# Docker execution
docker cp 1_core_builder/html_compiler.py stock_web:/app/1_core_builder/html_compiler.py
docker exec stock_web python3 1_core_builder/generate_report.py AAPL --lang EN
```
