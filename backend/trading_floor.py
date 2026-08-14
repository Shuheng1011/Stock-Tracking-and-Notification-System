from .traders import Trader
from typing import List
import asyncio
from .tracers import LogTracer
from agents import add_trace_processor
from .market import is_market_open
from dotenv import load_dotenv
import os

load_dotenv(override=True)

RUN_BETWEEN_AGENTS_MINUTES = int(os.getenv("RUN_BETWEEN_AGENTS_MINUTES", "15"))
RUN_EVEN_WHEN_MARKET_IS_CLOSED = (
    os.getenv("RUN_EVEN_WHEN_MARKET_IS_CLOSED", "false").strip().lower() == "true"
)
names = ["Warren", "George", "Ray", "Cathie"]
lastnames = ["Patience", "Bold", "Systematic", "Crypto"]
model_names = [
    "gpt-5.4-mini",
    "gpt-5.4-mini",
    "gpt-5.4-mini",
    "gpt-5.4-mini",
]
short_model_names = ["GPT 5.4 mini"] * 4


def create_traders() -> List[Trader]:
    traders = []
    for name, lastname, model_name in zip(names, lastnames, model_names):
        traders.append(Trader(name, lastname, model_name))
    return traders


async def run_agents_in_turn():
    add_trace_processor(LogTracer())
    traders = create_traders()
    while True:
        for trader in traders:
            if RUN_EVEN_WHEN_MARKET_IS_CLOSED or is_market_open():
                print(f"Running {trader.name}...", flush=True)
                await trader.run()
            else:
                print(f"Market is closed, skipping {trader.name}", flush=True)

            print(
                f"Waiting {RUN_BETWEEN_AGENTS_MINUTES} minutes before the next agent...",
                flush=True,
            )
            await asyncio.sleep(RUN_BETWEEN_AGENTS_MINUTES * 60)


if __name__ == "__main__":
    print(
        "Starting round-robin scheduler with "
        f"{RUN_BETWEEN_AGENTS_MINUTES} minutes between agents"
    )
    asyncio.run(run_agents_in_turn())
