# Business Cycle Backtester

Python toolkit for business-cycle and macro-regime index backtests.

It reads the index-level Excel workbook, calculates monthly index returns from
price history, joins the workbook's T-1 business-cycle and regime labels, maps
indexes to asset classes, and creates both CSV outputs and an HTML dashboard.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

```bash
python -m business_cycle_backtester.cli \
  --input-dir drive_downloads \
  --output-dir outputs \
  --index-workbook "/path/to/Business Cycle Backtest Index Level no bbg link.xlsx"
```

Required local files:

- `drive_downloads/US Business Cycle Model Final v.5.xlsx`
- `drive_downloads/US Regime Cycle Model v.2.xlsx`
- the index-level workbook passed with `--index-workbook`

Main outputs:

- `outputs/index_dashboard.html`
- `outputs/index_level_state_stats.csv`
- `outputs/asset_class_state_stats.csv`
- `outputs/index_asset_classes.csv`
- `outputs/business_cycle_signals.csv`
- `outputs/macro_regime_signals.csv`
- `outputs/all_state_stats.csv`
- `outputs/top_assets_by_state.csv`
- `outputs/summary.md`

## Sample Website

The repository also includes a static sample results website:

- `index.html`
- `styles.css`
- `app.js`
- `site-data.js`

It is designed to deploy directly on Vercel as a simple static site. The sample
data file is generated from the current backtest outputs and can be refreshed
after each new model run.

The first version reproduces the core research loop:

- classify ABCF business-cycle phase
- classify growth/inflation regime
- calculate index-level monthly returns from the index price workbook
- condition monthly index returns by phase, regime, and combined phase-regime state
- summarize equal-weighted returns by asset class
- calculate annualized return, volatility, Sharpe, hit rate, max drawdown, and transition matrices

## Notes

- The asset universe comes from the index-level workbook only.
- The dashboard includes index-level and asset-class summaries.
- T-1 phase/regime labels are used for cleaner no-lookahead research.
