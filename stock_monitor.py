import argparse
import logging
import os
import time
from datetime import datetime, timedelta
from typing import List, Optional

import requests
import yfinance as yf
from dotenv import load_dotenv

from huggingface_sentiment import analyze_sentiment

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY", "")
PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_APP_TOKEN", "")
STOCK_TICKERS = [item.strip().upper() for item in os.getenv("STOCK_TICKERS", "AAPL,MSFT,TSLA").split(",") if item.strip()]
CHANGE_THRESHOLD_PERCENT = float(os.getenv("CHANGE_THRESHOLD_PERCENT", "2.0"))
LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "3"))
POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", "15"))


def get_price_history(symbol: str):
    return yf.Ticker(symbol).history(period=f"{LOOKBACK_DAYS + 2}d", interval="1d", auto_adjust=True)


def calculate_change_pct(history) -> Optional[float]:
    if history is None or len(history) < 2:
        return None
    latest = float(history["Close"].iloc[-1])
    previous = float(history["Close"].iloc[-2])
    if previous == 0:
        return None
    return ((latest - previous) / previous) * 100


def get_recent_headlines(symbol: str, limit: int = 5) -> List[str]:
    try:
        ticker = yf.Ticker(symbol)
        articles = ticker.news or []
        headlines = []
        for article in articles[:limit]:
            title = article.get("title") or ""
            if title:
                headlines.append(title)
        return headlines
    except Exception as exc:
        logging.warning("Could not fetch Yahoo Finance news for %s: %s", symbol, exc)
        return []


def send_pushover_notification(symbol: str, change_pct: float, sentiment_score: float, headlines: List[str]) -> None:
    if not PUSHOVER_USER_KEY or not PUSHOVER_APP_TOKEN:
        logging.warning("Pushover credentials are missing; notification was not sent")
        return

    title = f"{symbol} dropped {change_pct:.2f}%"
    message = (
        f"{symbol} moved down {change_pct:.2f}% today. "
        f"Recent sentiment score: {sentiment_score:.2f}.\n"
        f"Latest headlines: {' | '.join(headlines[:3]) if headlines else 'No headlines available'}"
    )

    payload = {
        "token": PUSHOVER_APP_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "title": title,
        "message": message,
    }
    try:
        response = requests.post("https://api.pushover.net/1/messages.json", data=payload, timeout=15)
        response.raise_for_status()
        logging.info("Pushover notification sent for %s", symbol)
    except Exception as exc:
        logging.warning("Failed to send Pushover notification: %s", exc)


def monitor_once(tickers: List[str]) -> None:
    for symbol in tickers:
        try:
            history = get_price_history(symbol)
            change_pct = calculate_change_pct(history)
            if change_pct is None:
                continue

            if change_pct <= -CHANGE_THRESHOLD_PERCENT:
                headlines = get_recent_headlines(symbol)
                sentiment_score = analyze_sentiment(headlines)
                if sentiment_score < 0:
                    logging.info("Alert triggered for %s: %.2f%% drop, sentiment %.2f", symbol, change_pct, sentiment_score)
                    send_pushover_notification(symbol, change_pct, sentiment_score, headlines)
        except Exception as exc:
            logging.warning("Error monitoring %s: %s", symbol, exc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch stocks for a dip and send a Pushover alert when sentiment is negative")
    parser.add_argument("tickers", nargs="*", help="Stock tickers to monitor (for example AAPL MSFT TSLA)")
    parser.add_argument("--once", action="store_true", help="Run one check and exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tickers = [item.strip().upper() for item in args.tickers] if args.tickers else STOCK_TICKERS

    if args.once:
        monitor_once(tickers)
        return

    logging.info("Starting monitor for %s", ", ".join(tickers))
    while True:
        monitor_once(tickers)
        time.sleep(POLL_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
