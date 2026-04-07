# Loucas Di Pillo — Personal Portfolio

Personal portfolio website for Loucas Di Pillo, Economics & Finance student at HEC Liège.  
Built as a single-file static site with a companion Streamlit dashboard for live PEA portfolio tracking.

## Site

**`index.html`** — the entire portfolio website in one self-contained file.  
No build step, no framework, no dependencies. Open it directly in a browser or deploy to any static host.

Sections: Hero · About · Education · Experience · Skills · Projects · Gallery · Contact

### Assets
| Path | Contents |
|------|----------|
| `images/` | Profile photo and gallery images |
| `projects/` | PDF reports linked from project cards |
| `CV-Loucas_DiPillo.pdf` | CV linked from the hero section |

## PEA Dashboard

**`dashboard.py`** — a Streamlit app for tracking a French PEA (equity savings plan) ETF portfolio with live prices, time-weighted return, drawdown analysis, and historical snapshots.

```bash
pip install -r requirements.txt
streamlit run dashboard.py          # opens at http://localhost:8501
```

### Data files
| File | Purpose |
|------|---------|
| `portfolio.json` | Current positions (ticker, shares, avg buy price) |
| `history.json` | Snapshot history (date, cash flow, total invested, portfolio value) |

Both files are auto-created from defaults if missing.

## Project structure

```
portfolio/
├── index.html              # Portfolio website (self-contained)
├── CV-Loucas_DiPillo.pdf   # CV
├── images/                 # Gallery & profile photos
├── projects/               # Academic project PDFs
├── dashboard.py            # PEA portfolio Streamlit app
├── portfolio.json          # ETF positions data
├── history.json            # Portfolio snapshot history
├── requirements.txt        # Python dependencies
└── .streamlit/
    └── config.toml         # Dark theme config
```
