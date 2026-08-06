import OpenAI from "openai";

export async function createSummary(market, headlines) {
  if (!process.env.OPENAI_API_KEY) {
    return market
      .map((item) => `${item.symbol} closed at $${item.price.toFixed(2)}, ${item.changePercent >= 0 ? "up" : "down"} ${Math.abs(item.changePercent).toFixed(2)}%.`)
      .join(" ");
  }

  const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  const response = await client.responses.create({
    model: process.env.OPENAI_MODEL || "gpt-4.1-mini",
    instructions:
      "Write a factual daily market recap from only the supplied data. Use a 2-sentence overview followed by exactly 3 concise bullet points. Mention important movers and relevant headline context without implying causation. Do not give financial advice.",
    input: JSON.stringify({ market, headlines }),
  });
  return response.output_text;
}
