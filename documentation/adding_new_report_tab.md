# 📊 Developer Guide: Adding a New Report Tab/Module

This guide documents how to add a brand new module or analysis tab to the 13-tab master dashboard.

---

## 🛠️ Step-by-Step Procedure

### 1. Add Navigation Item
In `1_core_builder/html_compiler.py`, locate the `<aside class="sidebar">` navigation list and insert a new `nav-item`:

```html
<li class="nav-item" onclick="switchTab('newmodule')" data-i18n="tab_newmodule">
  {"⚡ 13. New Custom Module" if is_en else "⚡ 13. Yeni Özel Modül"}
</li>
```

### 2. Add Tab Pane Container
Inside `<main class="main-content">`, create a matching tab container div:

```html
<!-- TAB 13: NEW CUSTOM MODULE -->
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
    <!-- Insert module table, cards, or Chart.js canvas here -->
  </div>
</div>
```

### 3. Add i18n Translation Keys
Add matching keys to `1_core_builder/locales/en.json` and `1_core_builder/locales/tr.json`:

```json
"tab_newmodule": "⚡ 13. New Custom Module"
```

### 4. Verify & Build
Copy updated template to Docker container and build a test report:

```bash
docker cp 1_core_builder/html_compiler.py stock_web:/app/1_core_builder/html_compiler.py
docker exec stock_web python 1_core_builder/generate_report.py AAPL --lang EN
```
