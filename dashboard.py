"""
PEA Portfolio Dashboard
A Streamlit app for tracking a French tax-advantaged (PEA) ETF portfolio.

Run with:  streamlit run dashboard.py
"""

import json
import os
from datetime import date, datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PEA Portfolio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS (Catppuccin Mocha palette, polish on top of dark theme) ───────
st.markdown(
    """
<style>
/* ── Metric cards ─────────────────────────────────────── */
[data-testid="metric-container"] {
    background: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 14px;
    padding: 18px 22px;
}
[data-testid="stMetricLabel"] > div {
    color: #a6adc8 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 600;
}
[data-testid="stMetricValue"] > div {
    color: #cdd6f4 !important;
    font-size: 1.5rem !important;
    font-weight: 700;
}
/* ── Sidebar ──────────────────────────────────────────── */
section[data-testid="stSidebar"] > div {
    background: #181825 !important;
}
/* ── Navigation radio ─────────────────────────────────── */
div[data-testid="stVerticalBlock"] .stRadio label {
    padding: 6px 10px !important;
    border-radius: 8px;
    width: 100%;
    transition: background 0.15s;
}
div[data-testid="stVerticalBlock"] .stRadio label:hover {
    background: #313244 !important;
}
/* ── Misc ─────────────────────────────────────────────── */
hr { border-color: #313244 !important; margin: 8px 0 !important; }
h1 { color: #cdd6f4 !important; font-weight: 800 !important; letter-spacing: -0.02em; }
h2, h3 { color: #89b4fa !important; font-weight: 600 !important; }
.stCaption p { color: #6c7086 !important; }
.stProgress > div > div { background: #89b4fa !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ─── Palette & constants ──────────────────────────────────────────────────────
PORTFOLIO_FILE = "portfolio.json"
HISTORY_FILE = "history.json"

BG = "#11111b"
SURFACE = "#1e1e2e"
BORDER = "#313244"
TEXT = "#cdd6f4"
SUBTEXT = "#a6adc8"
MUTED = "#6c7086"

BLUE = "#89b4fa"
GREEN = "#a6e3a1"
RED = "#f38ba8"
PEACH = "#fab387"
MAUVE = "#cba6f7"
YELLOW = "#f9e2af"
TEAL = "#94e2d5"
SKY = "#74c7ec"

PALETTE = [BLUE, GREEN, PEACH, MAUVE, RED, YELLOW, TEAL, SKY]

_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor=BG,
    plot_bgcolor=BG,
    font=dict(color=TEXT, family="Inter, system-ui, sans-serif"),
    margin=dict(l=16, r=16, t=40, b=16),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
    ),
)

# ─── Seed data ────────────────────────────────────────────────────────────────
_DEFAULT_PORTFOLIO = {
    "positions": [
        {
            "ticker": "CW8.PA",
            "name": "Amundi MSCI World Swap",
            "shares": 6,
            "avg_buy_price": 589.2274,
        },
        {
            "ticker": "ETZ.PA",
            "name": "BNP Paribas Easy STOXX Europe 600",
            "shares": 54,
            "avg_buy_price": 18.167,
        },
        {
            "ticker": "PAEEM.PA",
            "name": "Amundi PEA MSCI Emerging ESG",
            "shares": 28,
            "avg_buy_price": 27.7306,
        },
        {
            "ticker": "CASH",
            "name": "Cash (EUR)",
            "shares": 126.90,
            "avg_buy_price": 1.0,
            "is_cash": True,
        },
    ]
}

_DEFAULT_HISTORY = {
    "snapshots": [
        {"date": "2025-09-18", "cash_flow":  3942.98, "total_invested": 3942.98, "portfolio_value": 3942.98},
        {"date": "2025-10-01", "cash_flow":   586.20, "total_invested": 4529.18, "portfolio_value": 4529.18},
        {"date": "2025-11-10", "cash_flow":    58.08, "total_invested": 4587.26, "portfolio_value": 4587.26},
        {"date": "2025-12-05", "cash_flow":    56.98, "total_invested": 4644.24, "portfolio_value": 4644.24},
        {"date": "2026-01-02", "cash_flow":    56.60, "total_invested": 4700.84, "portfolio_value": 4700.84},
        {"date": "2026-03-05", "cash_flow":   616.96, "total_invested": 5317.80, "portfolio_value": 5317.80},
        {"date": "2026-03-24", "cash_flow":   -87.52, "total_invested": 5230.28, "portfolio_value": 5234.24},
        {"date": "2026-03-31", "cash_flow":    58.60, "total_invested": 5288.88, "portfolio_value": 5292.84},
        {"date": "2026-04-07", "cash_flow":     0.00, "total_invested": 5288.88, "portfolio_value": 5582.75},
    ]
}

# ─── I/O ──────────────────────────────────────────────────────────────────────

def _load(path: str, default: dict) -> dict:
    if not os.path.exists(path):
        _save(path, default)
        return default
    with open(path) as f:
        return json.load(f)


def _save(path: str, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ─── Live prices (cached 5 min) ───────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_prices(tickers: tuple) -> dict:
    out = {}
    for tk in tickers:
        if tk == "CASH":
            out[tk] = 1.0  # cash is always worth 1 EUR per unit
            continue
        try:
            hist = yf.Ticker(tk).history(period="5d")
            out[tk] = float(hist["Close"].iloc[-1]) if not hist.empty else None
        except Exception:
            out[tk] = None
    return out


# ─── DataFrame builders ───────────────────────────────────────────────────────

def _build_positions(portfolio: dict, prices: dict) -> pd.DataFrame:
    rows = []
    for pos in portfolio["positions"]:
        tk = pos["ticker"]
        is_cash = pos.get("is_cash", False)
        shares = float(pos["shares"])
        avg = float(pos["avg_buy_price"])
        live = prices.get(tk)
        cost = shares * avg
        value = shares * live if live else None
        # Cash has no P&L (it's just stored euros)
        pnl = (value - cost) if (live and not is_cash) else (0.0 if is_cash else None)
        pnl_pct = (pnl / cost * 100) if (live and not is_cash) else (0.0 if is_cash else None)
        rows.append(
            dict(
                Ticker=tk,
                Name=pos["name"],
                Shares=shares,
                avg_buy=avg,
                live_price=live,
                value=value,
                pnl=pnl,
                pnl_pct=pnl_pct,
                is_cash=is_cash,
            )
        )
    return pd.DataFrame(rows)


def _build_history(history: dict) -> pd.DataFrame:
    df = pd.DataFrame(history["snapshots"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["peak"] = df["portfolio_value"].cummax()
    df["drawdown"] = (df["portfolio_value"] - df["peak"]) / df["peak"] * 100
    return df


# ─── Sidebar ──────────────────────────────────────────────────────────────────

def _sidebar(portfolio: dict, history: dict):
    with st.sidebar:
        st.markdown("## 📊 PEA Portfolio")
        st.caption("French tax-advantaged account")
        st.markdown("---")

        page = st.radio(
            "Navigate",
            ["Overview", "Allocation", "Positions", "Performance", "Drawdown"],
            label_visibility="collapsed",
        )

        st.markdown("---")

        if st.button("🔄  Refresh Live Prices", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")

        # ── Manage positions ──────────────────────────────────────────────
        with st.expander("⚙️  Manage Positions"):
            action = st.segmented_control(
                "Action", ["Add", "Edit", "Remove"], default="Add", label_visibility="collapsed"
            )

            if action == "Add":
                with st.form("frm_add", clear_on_submit=True):
                    tk = st.text_input("Ticker (Yahoo Finance)", placeholder="e.g. CW8.PA")
                    nm = st.text_input("Name", placeholder="e.g. Amundi MSCI World")
                    sh = st.number_input("Shares", min_value=0.0, step=0.001, format="%.4f")
                    pr = st.number_input("Avg Buy Price (€)", min_value=0.0, step=0.01, format="%.4f")
                    if st.form_submit_button("Add Position", use_container_width=True, type="primary"):
                        if tk and nm and sh > 0 and pr > 0:
                            portfolio["positions"].append(
                                dict(
                                    ticker=tk.upper().strip(),
                                    name=nm.strip(),
                                    shares=sh,
                                    avg_buy_price=pr,
                                )
                            )
                            _save(PORTFOLIO_FILE, portfolio)
                            st.success(f"Added {tk.upper()}")
                            st.rerun()
                        else:
                            st.warning("Fill all fields.")

            elif action == "Edit":
                opts = [p["ticker"] for p in portfolio["positions"]]
                if not opts:
                    st.info("No positions yet.")
                else:
                    sel = st.selectbox("Position", opts)
                    pos = next(p for p in portfolio["positions"] if p["ticker"] == sel)
                    with st.form("frm_edit"):
                        nm2 = st.text_input("Name", value=pos["name"])
                        sh2 = st.number_input("Shares", value=float(pos["shares"]), min_value=0.0, step=0.001, format="%.4f")
                        pr2 = st.number_input("Avg Buy (€)", value=float(pos["avg_buy_price"]), min_value=0.0, step=0.01, format="%.4f")
                        if st.form_submit_button("Save Changes", use_container_width=True):
                            pos.update(dict(name=nm2.strip(), shares=sh2, avg_buy_price=pr2))
                            _save(PORTFOLIO_FILE, portfolio)
                            st.success("Saved!")
                            st.rerun()

            else:  # Remove
                opts = [p["ticker"] for p in portfolio["positions"]]
                if not opts:
                    st.info("No positions yet.")
                else:
                    sel = st.selectbox("Position to remove", opts)
                    if st.button("Remove", type="primary", use_container_width=True):
                        portfolio["positions"] = [p for p in portfolio["positions"] if p["ticker"] != sel]
                        _save(PORTFOLIO_FILE, portfolio)
                        st.success(f"Removed {sel}")
                        st.rerun()

        # ── Log snapshot ──────────────────────────────────────────────────
        with st.expander("📅  Log Snapshot"):
            with st.form("frm_snap"):
                sn_date = st.date_input("Date", value=date.today())
                sn_val = st.number_input("Portfolio Value (€)", min_value=0.0, step=0.01, format="%.2f")
                sn_flow = st.number_input(
                    "Cash Flow (€)",
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    help="New deposit (+) or withdrawal (−) since last snapshot",
                )
                if st.form_submit_button("Log Snapshot", use_container_width=True, type="primary"):
                    if sn_val > 0:
                        snaps = history["snapshots"]
                        prev_inv = snaps[-1]["total_invested"] if snaps else 0.0
                        history["snapshots"].append(
                            dict(
                                date=sn_date.strftime("%Y-%m-%d"),
                                cash_flow=float(sn_flow),
                                total_invested=prev_inv + float(sn_flow),
                                portfolio_value=float(sn_val),
                            )
                        )
                        _save(HISTORY_FILE, history)
                        st.success("Snapshot saved!")
                        st.rerun()
                    else:
                        st.warning("Enter a valid portfolio value.")

        st.markdown("---")
        st.caption("Prices cached 5 min · Reference currency: EUR")

    return page, portfolio, history


# ─── Page helpers ─────────────────────────────────────────────────────────────

def _fmt_eur(val, decimals=2):
    return f"€ {val:,.{decimals}f}" if val is not None else "—"


def _delta_color(val):
    if val is None:
        return ""
    try:
        v = float(val)
        return f"color: {GREEN}; font-weight: 600" if v >= 0 else f"color: {RED}; font-weight: 600"
    except (TypeError, ValueError):
        return ""


# ─── TWR ──────────────────────────────────────────────────────────────────────

def _compute_twr(df_hist: pd.DataFrame) -> float | None:
    """Time-Weighted Return across all snapshot sub-periods.

    For each sub-period the return is computed on the value *before* the
    next cash flow, eliminating the distorting effect of contributions /
    withdrawals:  R_i = (V_end - CF_end) / V_start - 1
    """
    if len(df_hist) < 2:
        return None
    twr = 1.0
    for i in range(len(df_hist) - 1):
        v_start = df_hist["portfolio_value"].iloc[i]
        v_end   = df_hist["portfolio_value"].iloc[i + 1]
        cf      = df_hist["cash_flow"].iloc[i + 1]
        if v_start <= 0:
            continue
        twr *= (v_end - cf) / v_start
    return (twr - 1) * 100


# ─── Overview ─────────────────────────────────────────────────────────────────

def _page_overview(df_pos: pd.DataFrame, df_hist: pd.DataFrame, total_invested: float):
    st.title("📊 Overview")
    st.caption(f"Live as of {datetime.now().strftime('%d %b %Y · %H:%M:%S')}")
    st.markdown("---")

    has_prices = not df_pos["value"].isna().all()
    total_value = df_pos["value"].sum() if has_prices else None
    cost_basis = (df_pos["avg_buy"] * df_pos["Shares"]).sum()
    total_pnl = (df_pos["pnl"].sum()) if has_prices else None
    total_pnl_pct = (total_pnl / cost_basis * 100) if (has_prices and cost_basis) else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Invested", _fmt_eur(total_invested))
    c2.metric("Current Value", _fmt_eur(total_value) if has_prices else "—")
    c3.metric(
        "Total P&L",
        _fmt_eur(total_pnl) if has_prices else "—",
        delta=f"{total_pnl_pct:+.2f}%" if total_pnl_pct is not None else None,
        delta_color="normal",
    )
    c4.metric("Positions", len(df_pos))

    st.markdown("---")

    col_l, col_r = st.columns(2, gap="large")

    # Donut
    with col_l:
        st.subheader("Allocation")
        if has_prices:
            fig = go.Figure(
                go.Pie(
                    labels=df_pos["Name"],
                    values=df_pos["value"].fillna(0),
                    hole=0.62,
                    textinfo="percent+label",
                    textfont_size=11,
                    marker=dict(colors=PALETTE[: len(df_pos)], line=dict(color=BG, width=3)),
                    hovertemplate="<b>%{label}</b><br>€ %{value:,.2f} · %{percent}<extra></extra>",
                )
            )
            fig.add_annotation(
                text=f"€ {total_value:,.0f}",
                x=0.5,
                y=0.53,
                font=dict(size=17, color=TEXT),
                showarrow=False,
            )
            fig.add_annotation(
                text="portfolio",
                x=0.5,
                y=0.42,
                font=dict(size=11, color=MUTED),
                showarrow=False,
            )
            fig.update_layout(**_LAYOUT, height=320, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Live prices unavailable.")

    # Mini performance
    with col_r:
        st.subheader("Performance Snapshot")
        if len(df_hist) >= 2:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df_hist["date"],
                    y=df_hist["portfolio_value"],
                    mode="lines+markers",
                    name="Portfolio",
                    line=dict(color=BLUE, width=2.5),
                    fill="tozeroy",
                    fillcolor="rgba(137,180,250,0.07)",
                    hovertemplate="%{x|%d %b %Y}<br>€ %{y:,.2f}<extra>Portfolio</extra>",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df_hist["date"],
                    y=df_hist["total_invested"],
                    mode="lines",
                    name="Invested",
                    line=dict(color=GREEN, width=2, dash="dot"),
                    hovertemplate="%{x|%d %b %Y}<br>€ %{y:,.2f}<extra>Invested</extra>",
                )
            )
            fig.update_layout(
                **_LAYOUT,
                height=320,
                yaxis=dict(tickprefix="€ "),
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Log at least 2 snapshots to see the performance chart.")


# ─── Allocation ───────────────────────────────────────────────────────────────

def _page_allocation(df_pos: pd.DataFrame):
    st.title("🥧 Allocation")
    st.markdown("---")

    has_prices = not df_pos["value"].isna().all()
    if not has_prices:
        st.warning("Live prices unavailable — cannot compute allocation.")
        return

    total_value = df_pos["value"].sum()

    col_l, col_r = st.columns([3, 2], gap="large")

    with col_l:
        fig = go.Figure(
            go.Pie(
                labels=df_pos["Name"],
                values=df_pos["value"].fillna(0),
                hole=0.64,
                textinfo="percent+label",
                textfont_size=12,
                marker=dict(
                    colors=PALETTE[: len(df_pos)],
                    line=dict(color=BG, width=3),
                ),
                hovertemplate="<b>%{label}</b><br>€ %{value:,.2f} · %{percent}<extra></extra>",
            )
        )
        fig.add_annotation(
            text=f"€ {total_value:,.0f}",
            x=0.5,
            y=0.54,
            font=dict(size=20, color=TEXT),
            showarrow=False,
        )
        fig.add_annotation(
            text="total value",
            x=0.5,
            y=0.43,
            font=dict(size=11, color=MUTED),
            showarrow=False,
        )
        fig.update_layout(**_LAYOUT, height=480)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("Breakdown")
        for i, row in df_pos.iterrows():
            val = row["value"] or 0
            pct = val / total_value if total_value else 0
            color = PALETTE[i % len(PALETTE)]
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">'
                f'<span style="color:{color};font-weight:700;font-size:.95rem">{row["Ticker"]}</span>'
                f'<span style="color:{SUBTEXT};font-size:.82rem">{pct * 100:.1f}%</span>'
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div style="font-size:.8rem;color:{MUTED};margin-bottom:5px">{row["Name"]}</div>',
                unsafe_allow_html=True,
            )
            st.progress(pct)
            st.markdown(
                f'<div style="font-size:.85rem;color:{TEXT};margin-bottom:18px">€ {val:,.2f}</div>',
                unsafe_allow_html=True,
            )


# ─── Positions ────────────────────────────────────────────────────────────────

def _page_positions(df_pos: pd.DataFrame):
    st.title("📋 Positions")
    st.markdown("---")

    # For cash rows: show amount in Shares col, hide avg buy / live price columns
    display = df_pos.copy()
    display["live_price"] = display.apply(
        lambda r: None if r.get("is_cash") else r["live_price"], axis=1
    )
    display["avg_buy"] = display.apply(
        lambda r: None if r.get("is_cash") else r["avg_buy"], axis=1
    )
    display = display.rename(
        columns={
            "avg_buy": "Avg Buy (€)",
            "live_price": "Live Price (€)",
            "value": "Value (€)",
            "pnl": "P&L (€)",
            "pnl_pct": "P&L (%)",
        }
    )[["Ticker", "Name", "Shares", "Avg Buy (€)", "Live Price (€)", "Value (€)", "P&L (€)", "P&L (%)"]]

    styled = (
        display.style.format(
            {
                "Shares": "{:.4g}",
                "Avg Buy (€)": "€ {:,.4f}",
                "Live Price (€)": "€ {:,.4f}",
                "Value (€)": "€ {:,.2f}",
                "P&L (€)": "{:+,.2f} €",
                "P&L (%)": "{:+.2f}%",
            },
            na_rep="—",
        )
        .map(_delta_color, subset=["P&L (€)", "P&L (%)"])
        .hide(axis="index")
    )

    st.dataframe(styled, use_container_width=True, height=min(220 + len(df_pos) * 38, 420))

    st.markdown("---")

    # P&L bar chart (exclude cash — it always has 0 P&L and would be misleading)
    df_etf = df_pos[~df_pos.get("is_cash", pd.Series(False, index=df_pos.index))]
    if not df_etf["pnl"].isna().all():
        st.subheader("P&L by Position")
        pnl_vals = df_etf["pnl"].fillna(0).tolist()
        bar_colors = [GREEN if v >= 0 else RED for v in pnl_vals]
        fig = go.Figure(
            go.Bar(
                x=df_etf["Ticker"],
                y=pnl_vals,
                text=[f"€ {v:+,.2f}" for v in pnl_vals],
                textposition="outside",
                textfont=dict(size=13),
                marker=dict(color=bar_colors, line=dict(width=0)),
                hovertemplate="<b>%{x}</b><br>P&L: € %{y:+,.2f}<extra></extra>",
            )
        )
        fig.update_layout(
            **_LAYOUT,
            height=340,
            bargap=0.45,
            yaxis=dict(
                tickprefix="€ ",
                zeroline=True,
                zerolinecolor=BORDER,
                zerolinewidth=1,
            ),
        )
        st.plotly_chart(fig, use_container_width=True)


# ─── Performance ──────────────────────────────────────────────────────────────

def _page_performance(df_hist: pd.DataFrame, df_pos: pd.DataFrame):
    st.title("📈 Performance")
    st.markdown("---")

    if len(df_hist) < 2:
        st.info("Log at least 2 snapshots to see the performance chart.")
        return

    has_live = not df_pos["value"].isna().all()
    today_ts = pd.Timestamp(date.today())

    dates_plot = df_hist["date"].tolist()
    vals_plot = df_hist["portfolio_value"].tolist()
    inv_plot = df_hist["total_invested"].tolist()

    # Append live value as a "today" data point if market data is fresher
    if has_live and today_ts > df_hist["date"].iloc[-1]:
        dates_plot.append(today_ts)
        vals_plot.append(df_pos["value"].sum())
        inv_plot.append(df_hist["total_invested"].iloc[-1])

    fig = go.Figure()

    # Shaded fill between invested and portfolio
    fig.add_trace(
        go.Scatter(
            x=dates_plot + dates_plot[::-1],
            y=vals_plot + inv_plot[::-1],
            fill="toself",
            fillcolor="rgba(137,180,250,0.05)",
            line=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dates_plot,
            y=vals_plot,
            mode="lines+markers",
            name="Portfolio Value",
            line=dict(color=BLUE, width=2.5),
            marker=dict(size=7, color=BLUE, line=dict(width=1.5, color=BG)),
            fill="tozeroy",
            fillcolor="rgba(137,180,250,0.05)",
            hovertemplate="<b>%{x|%d %b %Y}</b><br>Value: € %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dates_plot,
            y=inv_plot,
            mode="lines+markers",
            name="Total Invested",
            line=dict(color=GREEN, width=2, dash="dot"),
            marker=dict(size=5, color=GREEN),
            hovertemplate="<b>%{x|%d %b %Y}</b><br>Invested: € %{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        **_LAYOUT,
        height=460,
        xaxis=dict(title="Date", showgrid=False, tickformat="%b %Y"),
        yaxis=dict(title="Value (€)", tickprefix="€ ", gridcolor=SURFACE),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    last_val = df_hist["portfolio_value"].iloc[-1]
    last_inv = df_hist["total_invested"].iloc[-1]
    twr = _compute_twr(df_hist)
    abs_pnl = last_val - last_inv
    days = (df_hist["date"].iloc[-1] - df_hist["date"].iloc[0]).days
    best_snap = df_hist.loc[df_hist["portfolio_value"].idxmax()]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TWR (Time-Weighted)", f"{twr:+.2f}%" if twr is not None else "—")
    c2.metric("Absolute P&L", f"€ {abs_pnl:+,.2f}")
    c3.metric("Total Invested", f"€ {last_inv:,.2f}")
    c4.metric("Portfolio High", f"€ {best_snap['portfolio_value']:,.2f}")


# ─── Drawdown ─────────────────────────────────────────────────────────────────

def _page_drawdown(df_hist: pd.DataFrame):
    st.title("📉 Drawdown Analysis")
    st.markdown("---")

    if len(df_hist) < 2:
        st.info("Log at least 2 snapshots to see the drawdown chart.")
        return

    min_idx = df_hist["drawdown"].idxmin()
    min_dd = df_hist["drawdown"].iloc[min_idx]
    min_date = df_hist["date"].iloc[min_idx]
    curr_dd = df_hist["drawdown"].iloc[-1]
    peak_val = df_hist["peak"].max()
    peak_date = df_hist.loc[df_hist["portfolio_value"].idxmax(), "date"]

    fig = go.Figure()

    # Zero baseline
    fig.add_hline(y=0, line_color=BORDER, line_width=1)

    fig.add_trace(
        go.Scatter(
            x=df_hist["date"],
            y=df_hist["drawdown"],
            mode="lines+markers",
            name="Drawdown from Peak",
            fill="tozeroy",
            fillcolor="rgba(243,139,168,0.12)",
            line=dict(color=RED, width=2.5),
            marker=dict(size=6, color=RED, line=dict(width=1.5, color=BG)),
            hovertemplate="<b>%{x|%d %b %Y}</b><br>Drawdown: %{y:.2f}%<extra></extra>",
        )
    )

    # Annotate max drawdown
    if min_dd < -0.01:
        fig.add_annotation(
            x=min_date,
            y=min_dd,
            text=f"  Max DD: {min_dd:.2f}%",
            showarrow=True,
            arrowhead=2,
            arrowcolor=RED,
            font=dict(color=RED, size=12),
            ax=50,
            ay=-36,
            bgcolor=SURFACE,
            bordercolor=RED,
            borderwidth=1,
            borderpad=5,
        )

    fig.update_layout(
        **_LAYOUT,
        height=420,
        xaxis=dict(title="Date", showgrid=False, tickformat="%b %Y"),
        yaxis=dict(
            title="Drawdown (%)",
            ticksuffix="%",
            zeroline=False,
            gridcolor=SURFACE,
        ),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Max Drawdown", f"{min_dd:.2f}%")
    c2.metric("Current Drawdown", f"{curr_dd:.2f}%")
    c3.metric("All-Time High", f"€ {peak_val:,.2f}")
    c4.metric("ATH Date", peak_date.strftime("%d %b %Y"))


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    portfolio = _load(PORTFOLIO_FILE, _DEFAULT_PORTFOLIO)
    history = _load(HISTORY_FILE, _DEFAULT_HISTORY)

    page, portfolio, history = _sidebar(portfolio, history)

    tickers = tuple(p["ticker"] for p in portfolio["positions"])

    with st.spinner("Fetching live prices…"):
        prices = _fetch_prices(tickers)

    df_pos = _build_positions(portfolio, prices)
    df_hist = _build_history(history)
    total_invested = df_hist["total_invested"].iloc[-1] if not df_hist.empty else 0.0

    if page == "Overview":
        _page_overview(df_pos, df_hist, total_invested)
    elif page == "Allocation":
        _page_allocation(df_pos)
    elif page == "Positions":
        _page_positions(df_pos)
    elif page == "Performance":
        _page_performance(df_hist, df_pos)
    elif page == "Drawdown":
        _page_drawdown(df_hist)


if __name__ == "__main__":
    main()
