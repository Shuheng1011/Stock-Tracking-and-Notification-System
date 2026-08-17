"""HTTP API over the trading floor, for a separate frontend to consume.

The Gradio dashboard in demo/ reads accounts.db in-process. This serves the same
data as JSON so a decoupled web frontend can render it. Everything here is
read-only; the trading floor writes the database out of band.

Run it from the 6_mcp directory so it shares the engine's accounts.db:

    uv run uvicorn backend.api:app --port 8000
"""

import json
import os
import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from openai import APIConnectionError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError

from backend import market
from backend.accounts import Account
from backend.database import read_log
from backend.trading_floor import names, lastnames, short_model_names

# Mirrors the log colours in demo/ so the frontend reproduces the same panel.
LOG_COLORS = {
    "trace": "#87CEEB",
    "agent": "#00dddd",
    "function": "#00dd00",
    "generation": "#dddd00",
    "response": "#aa00dd",
    "account": "#dd0000",
}
DEFAULT_LOG_COLOR = "#87CEEB"
SUMMARY_CACHE_SECONDS = 5 * 60
summary_cache: dict[str, dict] = {}

roster = [
    {"name": name, "lastname": lastname, "model_name": model_name}
    for name, lastname, model_name in zip(names, lastnames, short_model_names)
]
roster_by_name = {trader["name"].lower(): trader for trader in roster}

app = FastAPI(title="Trading Floor")


def average_cost(account: Account, symbol: str) -> float:
    """Average price paid across this symbol's buys, for per-holding profit."""
    spend = sum(t.price * t.quantity for t in account.transactions if t.symbol == symbol and t.quantity > 0)
    bought = sum(t.quantity for t in account.transactions if t.symbol == symbol and t.quantity > 0)
    return spend / bought if bought else 0.0


def holdings_detail(account: Account) -> list[dict]:
    """Current holdings enriched with price, market value and unrealised profit."""
    details = []
    for symbol, quantity in account.holdings.items():
        price = market.get_share_price(symbol)
        cost = average_cost(account, symbol)
        details.append(
            {
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "avg_cost": cost,
                "market_value": price * quantity,
                "unrealized_pnl": (price - cost) * quantity,
            }
        )
    return details


def require_trader(name: str) -> dict:
    trader = roster_by_name.get(name.lower())
    if not trader:
        raise HTTPException(status_code=404, detail=f"Unknown trader {name}")
    return trader


def summary_signature(account: Account) -> str:
    """A stable cache key that changes whenever the portfolio changes."""
    latest_transaction = account.transactions[-1].timestamp if account.transactions else None
    return json.dumps(
        {
            "balance": account.balance,
            "holdings": account.holdings,
            "transaction_count": len(account.transactions),
            "latest_transaction": latest_transaction,
            "strategy": account.strategy,
        },
        sort_keys=True,
        default=str,
    )


@app.get("/api/traders")
def get_traders() -> list[dict]:
    """The four traders on the floor."""
    return roster


@app.get("/api/market")
def get_market() -> dict:
    """Which price source is live, and whether the market is open."""
    return {
        "source": "massive",
        "configured": bool(market.massive_api_key),
        "is_market_open": market.is_market_open(),
    }


@app.get("/api/traders/{name}")
def get_trader(name: str) -> dict:
    """A trader's full state: value, profit, holdings, transactions and history."""
    trader = require_trader(name)
    account = Account.get(name)
    holdings = holdings_detail(account)
    portfolio_value = account.balance + sum(h["market_value"] for h in holdings)
    return {
        "name": trader["name"],
        "lastname": trader["lastname"],
        "model_name": trader["model_name"],
        "balance": account.balance,
        "strategy": account.strategy,
        "portfolio_value": portfolio_value,
        "pnl": account.calculate_profit_loss(portfolio_value),
        "holdings": holdings,
        "transactions": account.list_transactions(),
        "time_series": [{"datetime": ts, "value": value} for ts, value in account.portfolio_value_time_series],
    }


@app.post("/api/traders/{name}/summary")
def summarize_trader(name: str) -> dict:
    """Generate a concise, factual summary of one paper-trading portfolio."""
    trader = require_trader(name)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Portfolio summaries require OPENAI_API_KEY.")

    account = Account.get(name)
    signature = summary_signature(account)
    cache_key = trader["name"].lower()
    cached = summary_cache.get(cache_key)
    now = time.time()
    if (
        cached
        and cached["signature"] == signature
        and now - cached["created_at"] < SUMMARY_CACHE_SECONDS
    ):
        return {**cached["payload"], "cached": True}

    holdings = holdings_detail(account)
    portfolio_value = account.balance + sum(item["market_value"] for item in holdings)
    pnl = account.calculate_profit_loss(portfolio_value)
    model_input = {
        "trader": trader,
        "cash": account.balance,
        "portfolio_value": portfolio_value,
        "profit_loss": pnl,
        "holdings": holdings,
        "recent_transactions": account.list_transactions()[-5:],
        "strategy": account.strategy,
    }

    try:
        client = OpenAI(api_key=api_key, timeout=30.0)
        response = client.responses.create(
            model=os.getenv("SUMMARY_MODEL", "gpt-5.4-mini"),
            instructions=(
                "Summarize this paper-trading portfolio using only the supplied data. "
                "Explain its current value and cash allocation, principal holdings, total "
                "profit or loss, and the most recent decision when one exists. Use no more "
                "than three short paragraphs. Do not invent market events, imply unsupported "
                "causation, give financial advice, or recommend a trade."
            ),
            input=json.dumps(model_input, default=str),
        )
    except AuthenticationError as error:
        raise HTTPException(status_code=503, detail="The summary service is not configured correctly.") from error
    except RateLimitError as error:
        raise HTTPException(status_code=429, detail="The summary service is busy. Please try again shortly.") from error
    except APITimeoutError as error:
        raise HTTPException(status_code=504, detail="The summary request timed out. Please try again.") from error
    except APIConnectionError as error:
        raise HTTPException(status_code=502, detail="The summary service could not be reached.") from error

    summary = response.output_text.strip()
    if not summary:
        raise HTTPException(status_code=502, detail="The summary service returned an empty response.")

    payload = {
        "summary": summary,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cached": False,
    }
    summary_cache[cache_key] = {
        "signature": signature,
        "created_at": now,
        "payload": payload,
    }
    return payload


@app.get("/api/traders/{name}/logs")
def get_trader_logs(name: str, last_n: int = 13) -> list[dict]:
    """Recent trace and account log lines, oldest first, with their panel colour."""
    require_trader(name)
    rows = list(read_log(name, last_n))
    return [
        {"datetime": ts, "type": kind, "message": message, "color": LOG_COLORS.get(kind, DEFAULT_LOG_COLOR)}
        for ts, kind, message in rows
    ]
