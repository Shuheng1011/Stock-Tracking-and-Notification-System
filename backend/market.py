"""Live share prices from the Massive market data API."""

import os
import time
from threading import Lock

from dotenv import load_dotenv
from massive import RESTClient

load_dotenv(override=True)

massive_api_key = os.getenv("MASSIVE_API_KEY")
PRICE_CACHE_SECONDS = int(os.getenv("MARKET_PRICE_CACHE_SECONDS", "300"))

# Price requests arrive concurrently when the dashboard refreshes all traders.
# A shared cache and lock prevent each panel from making the same Massive call.
price_cache: dict[str, tuple[float, float]] = {}
price_cache_lock = Lock()


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


def _is_rate_limited(error: Exception) -> bool:
    """Whether an exception or one of its causes represents HTTP 429."""
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        response = getattr(current, "response", None)
        if getattr(response, "status", None) == 429 or getattr(response, "status_code", None) == 429:
            return True
        if "429" in str(current):
            return True
        current = current.__cause__ or current.__context__
    return False


def get_share_price(symbol: str) -> float:
    """Return a live Massive price; never substitute simulated market data."""
    if not massive_api_key:
        raise RuntimeError("MASSIVE_API_KEY is required for live share prices")
    return get_share_price_massive(symbol)


def get_share_price_massive(symbol: str) -> float:
    """Return a cached price or fetch the best price allowed by the plan."""
    global plan_tier
    symbol = symbol.upper()

    with price_cache_lock:
        now = time.monotonic()
        cached = price_cache.get(symbol)
        if cached and now - cached[1] < PRICE_CACHE_SECONDS:
            return cached[0]

        client = RESTClient(massive_api_key)
        last_error = None
        for tier in range(plan_tier, len(price_methods)):
            try:
                price = price_methods[tier](client, symbol)
                if price <= 0:
                    raise ValueError(f"Massive returned an invalid price for {symbol}: {price}")
                plan_tier = tier
                price_cache[symbol] = (price, now)
                return price
            except Exception as error:
                last_error = error
                # Retrying another endpoint cannot bypass an account-wide rate limit.
                if _is_rate_limited(error):
                    break

        # Keep the dashboard usable during a temporary outage or rate-limit window.
        if cached:
            return cached[0]
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
