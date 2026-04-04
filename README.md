# PEA Portfolio Dashboard

A dark-themed Streamlit dashboard for tracking a French PEA (Plan d'Épargne en Actions) ETF portfolio, with live prices via yfinance and historical performance tracking.

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the dashboard
streamlit run dashboard.py
```

The app opens at **http://localhost:8501** with a forced dark theme.

## Features

| Page | What you see |
|---|---|
| **Overview** | Total invested · current value · total P&L (€ + %) · mini allocation donut + performance snapshot |
| **Allocation** | Full donut chart with per-position breakdown and progress bars |
| **Positions** | Colour-coded table (live price, P&L per position) + P&L bar chart |
| **Performance** | Portfolio value vs. total invested over time (with live data point if fresher) |
| **Drawdown** | Rolling drawdown from all-time high, max-DD annotation, ATH metrics |

**Sidebar controls:**
- **Refresh Live Prices** — clears the 5-minute cache and re-fetches
- **Manage Positions** — add, edit, or remove ETF positions (persisted to `portfolio.json`)
- **Log Snapshot** — record a portfolio value + optional cash flow (persisted to `history.json`)

## Data files

| File | Purpose |
|---|---|
| `portfolio.json` | Current positions (ticker, name, shares, avg buy price) |
| `history.json` | Snapshot history (date, cash flow, total invested, portfolio value) |

Both files are created automatically on first run if missing, pre-seeded with your PEA positions and historical snapshots.

## Project structure

```
portfolio/
├── dashboard.py          # Main Streamlit app
├── portfolio.json        # Position data
├── history.json          # Historical snapshots
├── requirements.txt
├── README.md
└── .streamlit/
    └── config.toml       # Dark theme config
```

## Requirements

- Python 3.10+
- See `requirements.txt` (streamlit, yfinance, pandas ≥ 2.1, plotly, numpy)
