# 🧮 Developer Guide: Adding a New Financial Metric

This guide explains how to add new financial formulas, quantitative ratios, or forensic risk metrics to the analysis pipeline.

---

## 🛠️ Step-by-Step Procedure

### 1. Define Formula in Data Sourcing Module
In `1_core_builder/fetch_yfinance.py`, locate or create metric computation helper functions.

Example: Adding **Free Cash Flow Yield (FCF Yield)**:
```python
def compute_fcf_yield(fcf: float, market_cap: float) -> float:
    """Calculates Free Cash Flow Yield (%) = FCF / Market Cap."""
    if not market_cap or market_cap <= 0:
        return 0.0
    return round((fcf / market_cap) * 100, 2)
```

### 2. Include Metric in Quantitative Summary
Update `fetch_stock_metrics(ticker)` in `1_core_builder/fetch_yfinance.py` to return the new metric in the returned dictionary:

```python
metrics["fcf_yield_pct"] = compute_fcf_yield(metrics["recent_fcf"], metrics["market_cap"])
```

### 3. Display Metric in HTML Compiler
In `1_core_builder/html_compiler.py`, locate the relevant table (e.g. Executive Key Metrics or Scorecard):

```python
<tr>
  <td><strong>{"FCF Yield (%)" if is_en else "FCF Verimi (%)"}</strong></td>
  <td><strong>{_fmt_pct(metrics.get("fcf_yield_pct", 0)/100, is_en=is_en)}</strong></td>
  <td>> 5.0%</td>
  <td><span class="{"tag-green" if metrics.get("fcf_yield_pct", 0) >= 5 else "tag-amber"}">
    {("🟢 High Cash Generation" if metrics.get("fcf_yield_pct", 0) >= 5 else "🟡 Low Yield") if is_en else ("🟢 Yüksek Nakit Üretimi" if metrics.get("fcf_yield_pct", 0) >= 5 else "🟡 Düşük Verim")}
  </span></td>
</tr>
```

### 4. Verify & Unit Test
Add a unit test in `tests/test_fetch_yfinance.py`:

```python
def test_compute_fcf_yield(self):
    from fetch_yfinance import compute_fcf_yield
    self.assertEqual(compute_fcf_yield(100_000_000, 2_000_000_000), 5.0)
```

Run test suite:
```bash
python tests/run_tests.py
```
