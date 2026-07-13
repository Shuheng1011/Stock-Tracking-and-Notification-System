import logging
import os
from functools import lru_cache
from typing import List

from transformers import pipeline

HF_MODEL_NAME = os.getenv("HF_MODEL_NAME", "ProsusAI/finbert")
HF_SENTIMENT_DEVICE = os.getenv("HF_SENTIMENT_DEVICE", "cpu")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@lru_cache(maxsize=1)
def get_sentiment_pipeline():
    device = -1 if str(HF_SENTIMENT_DEVICE).lower() == "cpu" else 0
    return pipeline(
        "sentiment-analysis",
        model=HF_MODEL_NAME,
        tokenizer=HF_MODEL_NAME,
        device=device,
        truncation=True,
    )


def analyze_sentiment(headlines: List[str]) -> float:
    if not headlines:
        return 0.0

    try:
        classifier = get_sentiment_pipeline()
        results = classifier(headlines[:5], truncation=True)
    except Exception as exc:
        logging.warning("Hugging Face sentiment analysis failed: %s", exc)
        return 0.0

    sentiment_values = []
    for result in results:
        label = str(result.get("label", "")).lower()
        score = float(result.get("score", 0.0))
        if label.startswith("pos"):
            sentiment_values.append(score)
        elif label.startswith("neg"):
            sentiment_values.append(-score)
        else:
            sentiment_values.append(0.0)

    if not sentiment_values:
        return 0.0
    return sum(sentiment_values) / len(sentiment_values)
