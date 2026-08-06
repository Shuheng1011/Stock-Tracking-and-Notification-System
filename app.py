"""Streamlit stock and portfolio dashboard."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
SERPAPI_URL = "https://serpapi.com/search.json"
DEFAULT_POSITIONS = [
    {"symbol": "AAPL", "shares": 10.0, "average_cost": 185.0},
    {"symbol": "MSFT", "shares": 5.0, "average_cost": 410.0},
    {"symbol": "NVDA", "shares": 8.0, "average_cost": 120.0},
]


st.set_page_config(page_title="Northstar Portfolio", page_icon="📈", layout="wide")
st.markdown(
    """
    <style>
    .block-container {max-width: 1450px; padding-top: 2rem;}
    [data-testid="stMetric"] {background: #121a2b; border: 1px solid #26334d;
        border-radius: 14px; padding: 16px 18px;}
    [data-testid="stMetricValue"] {font-size: 1.75rem;}
    .eyebrow {color: #56d6b0; font-size: .78rem; font-weight: 700;
        letter-spacing: .15em; text-transform: uppercase;}
    .subtle {color: #8fa0bb;}
    .news-card {border-left: 3px solid #56d6b0; padding: 2px 0 2px 14px; margin: 14px 0;}
    </style>
    """,
    unsafe_allow_html=True,
)


def env_key(name: str) -> str:
    return os.getenv(name, "").strip()


@st.cache_data(ttl=300, show_spinner=False)
def get_quote(symbol: str, api_key: str) -> dict[str, Any]:
    response = requests.get(
        ALPHA_VANTAGE_URL,
        params={"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": api_key},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("Note") or data.get("Information"):
        raise RuntimeError(data.get("Note") or data.get("Information"))
    quote = data.get("Global Quote", {})
    if not quote:
        raise RuntimeError(f"No quote returned for {symbol}.")
    return {
        "price": float(quote["05. price"]),
        "change": float(quote["09. change"]),
        "change_pct": float(quote["10. change percent"].rstrip("%")),
        "latest_day": quote["07. latest trading day"],
    }


@st.cache_data(ttl=900, show_spinner=False)
def get_history(symbol: str, api_key: str) -> pd.DataFrame:
    response = requests.get(
        ALPHA_VANTAGE_URL,
        params={"function": "TIME_SERIES_DAILY", "symbol": symbol, "outputsize": "compact", "apikey": api_key},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("Note") or data.get("Information"):
        raise RuntimeError(data.get("Note") or data.get("Information"))
    series = data.get("Time Series (Daily)")
    if not series:
        raise RuntimeError(f"No price history returned for {symbol}.")
    rows = [
        {"date": pd.to_datetime(day), "close": float(values["4. close"]), "volume": int(values["5. volume"])}
        for day, values in series.items()
    ]
    return pd.DataFrame(rows).sort_values("date")


@st.cache_data(ttl=1800, show_spinner=False)
def get_news(symbol: str, api_key: str) -> list[dict[str, str]]:
    response = requests.get(
        SERPAPI_URL,
        params={"engine": "google_news", "q": f"{symbol} stock", "api_key": api_key, "hl": "en", "gl": "us"},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError(data["error"])
    items = []
    for result in data.get("news_results", [])[:6]:
        source = result.get("source", {})
        items.append({
            "title": result.get("title", "Untitled"),
            "link": result.get("link", "#"),
            "source": source.get("name", "News") if isinstance(source, dict) else str(source),
            "date": result.get("date", ""),
        })
    return items


def money(value: float) -> str:
    return f"${value:,.2f}"


def build_briefing(rows: list[dict[str, Any]], openai_key: str) -> str:
    snapshot = "\n".join(
        f"{row['symbol']}: {row['shares']} shares, value {money(row['market_value'])}, "
        f"unrealized P/L {money(row['gain'])} ({row['gain_pct']:+.2f}%), day move {row['change_pct']:+.2f}%"
        for row in rows
    )
    client = OpenAI(api_key=openai_key)
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        instructions=(
            "You are a concise portfolio analyst. Summarize only the supplied numbers. "
            "Highlight concentration and notable movers, state that this is not financial advice, "
            "and never invent news or prices. Use 3 short bullets."
        ),
        input=f"Portfolio snapshot:\n{snapshot}",
    )
    return response.output_text


if "positions" not in st.session_state:
    st.session_state.positions = DEFAULT_POSITIONS.copy()

alpha_key = env_key("ALPHA_VANTAGE_API_KEY") or env_key("ALPHAVANTAGE_API_KEY")
serp_key = env_key("SERPA_API_KEY") or env_key("SERPAPI_API_KEY")
openai_key = env_key("OPENAI_API_KEY")

with st.sidebar:
    st.markdown("### Northstar")
    st.caption("Personal market command center")
    page = st.radio("View", ["Portfolio", "Stock research"], label_visibility="collapsed")
    st.divider()
    st.markdown("**Connections**")
    for label, present in [("Alpha Vantage", alpha_key), ("SerpAPI", serp_key), ("OpenAI", openai_key)]:
        st.caption(f"{'🟢' if present else '🔴'} {label}")
    st.divider()
    with st.expander("Add a position"):
        with st.form("add_position", clear_on_submit=True):
            new_symbol = st.text_input("Ticker", placeholder="SHOP").upper().strip()
            new_shares = st.number_input("Shares", min_value=0.0001, value=1.0, step=1.0)
            new_cost = st.number_input("Average cost", min_value=0.0, value=100.0, step=1.0)
            if st.form_submit_button("Add position", use_container_width=True) and new_symbol:
                st.session_state.positions.append(
                    {"symbol": new_symbol, "shares": float(new_shares), "average_cost": float(new_cost)}
                )
                st.rerun()
    if st.button("Reset demo portfolio", use_container_width=True):
        st.session_state.positions = DEFAULT_POSITIONS.copy()
        st.rerun()

st.markdown('<div class="eyebrow">Market overview</div>', unsafe_allow_html=True)
st.title("Portfolio dashboard" if page == "Portfolio" else "Stock research")
st.caption(f"Last refreshed {datetime.now().strftime('%b %d, %Y · %I:%M %p')} · Quotes may be delayed")

if not alpha_key:
    st.error("Add ALPHA_VANTAGE_API_KEY to your .env file to load market data.")
    st.stop()

if page == "Portfolio":
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    with st.spinner("Loading portfolio quotes…"):
        for position in st.session_state.positions:
            try:
                quote = get_quote(position["symbol"], alpha_key)
                value = position["shares"] * quote["price"]
                cost = position["shares"] * position["average_cost"]
                rows.append({**position, **quote, "market_value": value, "cost_basis": cost,
                             "gain": value - cost, "gain_pct": ((value - cost) / cost * 100) if cost else 0.0})
            except Exception as exc:
                errors.append(f"{position['symbol']}: {exc}")

    if errors:
        st.warning("Some quotes could not be loaded. Alpha Vantage's free tier has a low request limit.\n\n" + "\n\n".join(errors))
    if not rows:
        st.stop()

    total_value = sum(row["market_value"] for row in rows)
    total_cost = sum(row["cost_basis"] for row in rows)
    total_gain = total_value - total_cost
    day_change = sum(row["market_value"] * row["change_pct"] / (100 + row["change_pct"]) for row in rows)
    cols = st.columns(4)
    cols[0].metric("Portfolio value", money(total_value))
    cols[1].metric("Total return", money(total_gain), f"{(total_gain / total_cost * 100) if total_cost else 0:+.2f}%")
    cols[2].metric("Today's move", money(day_change), f"{(day_change / (total_value-day_change) * 100) if total_value != day_change else 0:+.2f}%")
    cols[3].metric("Positions", len(rows), f"{len({r['symbol'] for r in rows})} symbols")

    left, right = st.columns([1.7, 1], gap="large")
    with left:
        st.subheader("Holdings")
        display = pd.DataFrame(rows)
        display = display[["symbol", "shares", "price", "market_value", "average_cost", "gain", "gain_pct", "change_pct"]]
        display.columns = ["Symbol", "Shares", "Price", "Market value", "Avg. cost", "Return", "Return %", "Day %"]
        st.dataframe(
            display.style.format({"Shares": "{:,.2f}", "Price": "${:,.2f}", "Market value": "${:,.2f}",
                                  "Avg. cost": "${:,.2f}", "Return": "${:+,.2f}", "Return %": "{:+.2f}%", "Day %": "{:+.2f}%"}),
            hide_index=True, use_container_width=True,
        )
    with right:
        st.subheader("Allocation")
        fig = go.Figure(go.Pie(labels=[r["symbol"] for r in rows], values=[r["market_value"] for r in rows], hole=.68))
        fig.update_traces(textinfo="label+percent", marker={"colors": ["#56d6b0", "#5d8ef7", "#ba7df4", "#f2bd5c", "#f47f79"]})
        fig.update_layout(height=315, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
                          paper_bgcolor="rgba(0,0,0,0)", font_color="#dce6f7")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("AI portfolio briefing")
    if not openai_key:
        st.info("Add OPENAI_API_KEY to enable the briefing.")
    elif st.button("Generate briefing", type="primary"):
        try:
            with st.spinner("Analyzing the current snapshot…"):
                st.markdown(build_briefing(rows, openai_key))
        except Exception as exc:
            st.error(f"Briefing unavailable: {exc}")

else:
    symbol = st.text_input("Search a ticker", value="AAPL", max_chars=12).upper().strip()
    if symbol:
        try:
            quote = get_quote(symbol, alpha_key)
            history = get_history(symbol, alpha_key)
            st.metric(symbol, money(quote["price"]), f"{quote['change']:+.2f} ({quote['change_pct']:+.2f}%)")
            fig = go.Figure(go.Scatter(x=history["date"], y=history["close"], mode="lines", fill="tozeroy",
                                       line={"color": "#56d6b0", "width": 2}, fillcolor="rgba(86,214,176,.08)"))
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10), xaxis_title=None, yaxis_title="USD",
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#aebbd0",
                              hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as exc:
            st.error(f"Market data unavailable: {exc}")

        st.subheader("Latest news")
        if not serp_key:
            st.info("Add SERPA_API_KEY to enable news.")
        else:
            try:
                for article in get_news(symbol, serp_key):
                    st.markdown(
                        f'<div class="news-card"><a href="{article["link"]}" target="_blank"><b>{article["title"]}</b></a>'
                        f'<br><span class="subtle">{article["source"]} · {article["date"]}</span></div>',
                        unsafe_allow_html=True,
                    )
            except Exception as exc:
                st.error(f"News unavailable: {exc}")

st.divider()
st.caption("For informational purposes only. Market data may be delayed and does not constitute financial advice.")
