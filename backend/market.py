"""Live share prices from the Massive market data API."""

import os
from dotenv import load_dotenv
from massive import RESTClient

load_dotenv(override=True)

massive_api_key = os.getenv("MASSIVE_API_KEY")


def _last_trade(client: RESTClient, symbol: str) -> float:
    return float(client.get_last_trade(symbol).price)


def _snapshot(client: RESTClient, symbol: str) -> float:
    snapshot = client.get_snapshot_ticker("stocks", symbol)
    return float(snapshot.min.close or snapshot.prev_day.close)


def _previous_close(client: RESTClient, symbol: str) -> float:
    return float(client.get_previous_close_agg(symbol)[0].close)


# Best price first, prior close last. Lower tier plans reject the earlier calls,
# so we remember the first tier that works and start there next time.
price_methods = [_last_trade, _snapshot, _previous_close]
plan_tier = 0


def get_share_price(symbol: str) -> float:
    """Return a live Massive price; never substitute simulated market data."""
    if not massive_api_key:
        raise RuntimeError("MASSIVE_API_KEY is required for live share prices")
    return get_share_price_massive(symbol)


def get_share_price_massive(symbol: str) -> float:
    """Best price the plan allows, remembering the working tier to avoid repeat failures."""
    global plan_tier
    client = RESTClient(massive_api_key)
    last_error = None
    for tier in range(plan_tier, len(price_methods)):
        try:
            price = price_methods[tier](client, symbol)
            if price <= 0:
                raise ValueError(f"Massive returned an invalid price for {symbol}: {price}")
            plan_tier = tier
            return price
        except Exception as error:
            last_error = error
            continue
    raise RuntimeError(f"No live Massive price available for {symbol}") from last_error


def is_market_open() -> bool:
    """Whether Massive reports that the US market is open."""
    if not massive_api_key:
        return False
    try:
        client = RESTClient(massive_api_key)
        return client.get_market_status().market == "open"
    except Exception as error:
        print(f"Unable to read Massive market status: {error}")
        return False
