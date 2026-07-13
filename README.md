# Stock dip monitor

This starter project watches a list of stock tickers, checks whether their latest close dropped by a configurable percentage, and then looks at recent headlines to see whether sentiment is negative before sending a Pushover notification.

## Setup

1. Create a virtual environment if you want.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the example environment file and fill in your credentials:
   ```bash
   copy .env.example .env
   ```
4. Run once:
   ```bash
   python stock_monitor.py AAPL MSFT TSLA --once
   ```

## Required services

- Pushover app token and user key

## Notes

- The script uses yfinance to fetch both stock history and recent Yahoo Finance headlines.
- Sentiment is now powered by a Hugging Face model via the Transformers library.
- The default model is ProsusAI/finbert, which is a strong general-purpose finance sentiment model.
- For production use, you may still want to cache results, add rate limiting, or swap in a fine-tuned finance-specific model.
