import argparse
import os
import re
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv
from langchain.agents import AgentType, Tool, initialize_agent
from langchain.llms import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
DEFAULT_SYMBOLS = os.getenv("DEFAULT_MARKET_SYMBOLS", "AAPL,MSFT,GOOGL,AMZN,TSLA")
DEFAULT_DAYS = int(os.getenv("DEFAULT_MARKET_DAYS", "3"))
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

if not OPENAI_API_KEY:
    raise EnvironmentError("Missing OPENAI_API_KEY in environment or .env file.")

if not ALPHAVANTAGE_API_KEY:
    raise EnvironmentError("Missing ALPHAVANTAGE_API_KEY in environment or .env file.")


def clean_symbol_list(symbol_text: str) -> List[str]:
    raw_symbols = re.split(r"[\s,;]+", symbol_text or "")
    symbols = [symbol.strip().upper() for symbol in raw_symbols if symbol.strip()]
    return symbols if symbols else clean_symbol_list(DEFAULT_SYMBOLS)


def fetch_daily_alpha(symbol: str) -> Dict[str, Any]:
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": symbol,
        "apikey": ALPHAVANTAGE_API_KEY,
        "outputsize": "compact",
        "datatype": "json",
    }
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()

    if "Error Message" in data:
        raise ValueError(f"AlphaVantage returned an error for {symbol}: {data['Error Message']}")
    if "Note" in data:
        raise ValueError(f"AlphaVantage note for {symbol}: {data['Note']}")
    if "Time Series (Daily)" not in data:
        raise ValueError(f"Unable to parse AlphaVantage daily data for {symbol}: {data}")

    return data["Time Series (Daily)"]


def create_market_snapshot(symbol: str, days: int = 3) -> str:
    daily_data = fetch_daily_alpha(symbol)
    sorted_dates = sorted(daily_data.keys(), reverse=True)
    requested_dates = sorted_dates[: max(days, 2)]

    if len(requested_dates) < 2:
        raise ValueError(f"Not enough daily data for {symbol} to build a recap.")

    latest_date = requested_dates[0]
    prior_date = requested_dates[1]
    latest_quote = daily_data[latest_date]
    prior_quote = daily_data[prior_date]

    latest_close = float(latest_quote["4. close"])
    prior_close = float(prior_quote["4. close"])
    change = latest_close - prior_close
    change_pct = (change / prior_close) * 100 if prior_close else 0.0

    daily_summary = [
        f"{symbol} — latest trading day {latest_date}: close ${latest_close:.2f}, change {change:+.2f} ({change_pct:+.2f}%).",
        f"Open ${float(latest_quote['1. open']):.2f}, high ${float(latest_quote['2. high']):.2f}, low ${float(latest_quote['3. low']):.2f}.",
        f"Previous close on {prior_date} was ${prior_close:.2f}.",
    ]

    if len(requested_dates) > 2:
        range_close = float(daily_data[requested_dates[-1]]["4. close"])
        longer_change = latest_close - range_close
        longer_pct = (longer_change / range_close) * 100 if range_close else 0.0
        daily_summary.append(
            f"Over the last {len(requested_dates)} trading days, {symbol} moved {longer_change:+.2f} ({longer_pct:+.2f}%)."
        )

    return " ".join(daily_summary)


def fetch_recent_market_data(tool_input: str) -> str:
    symbols = DEFAULT_SYMBOLS
    days = DEFAULT_DAYS

    symbol_match = re.search(r"(?:for|symbols?)[\s:]*([A-Za-z0-9,\s]+)", tool_input, re.IGNORECASE)
    if symbol_match:
        symbols = symbol_match.group(1)

    days_match = re.search(r"last\s+(\d+)\s+(?:day|days|trading days)", tool_input, re.IGNORECASE)
    if days_match:
        days = int(days_match.group(1))

    symbol_list = clean_symbol_list(symbols)
    symbol_list = symbol_list[:5]

    snapshots = []
    for symbol in symbol_list:
        try:
            snapshots.append(create_market_snapshot(symbol, days=days))
        except Exception as exc:
            snapshots.append(f"{symbol} data error: {exc}")

    return "\n".join(snapshots)


def create_market_recap_agent() -> Any:
    llm = OpenAI(temperature=0, model_name=DEFAULT_OPENAI_MODEL)
    tools = [
        Tool(
            name="MarketDataFetcher",
            func=fetch_recent_market_data,
            description=(
                "Fetch recent daily equity data for one or more US stock symbols and return a short data summary. "
                "The input should describe the ticker symbols and the number of trading days."
            ),
        )
    ]
    return initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=False,
        max_iterations=3,
    )


def create_daily_recap(symbols: str = DEFAULT_SYMBOLS, days: int = DEFAULT_DAYS) -> str:
    agent = create_market_recap_agent()
    query = (
        f"Create a daily market recap for the following ticker symbols: {symbols}. "
        f"Use the last {days} trading days of data to describe price movement, volatility, and important trends."
    )
    return agent.run(query)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a LangChain agent to produce a daily market recap.")
    parser.add_argument(
        "--symbols",
        type=str,
        default=DEFAULT_SYMBOLS,
        help="Comma-separated list of stock symbols to include in the recap.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help="Number of trading days to include in the recap.",
    )
    args = parser.parse_args()

    recap = create_daily_recap(args.symbols, args.days)
    print(recap)
