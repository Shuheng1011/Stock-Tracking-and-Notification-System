const ALPHA_URL = "https://www.alphavantage.co/query";
const SERP_URL = "https://serpapi.com/search.json";

async function readJson(response, service) {
  if (!response.ok) throw new Error(`${service} request failed (${response.status}).`);
  return response.json();
}

export async function fetchQuote(symbol) {
  const url = new URL(ALPHA_URL);
  url.search = new URLSearchParams({
    function: "GLOBAL_QUOTE",
    symbol,
    apikey: process.env.ALPHA_VANTAGE_API_KEY,
  });
  const data = await readJson(await fetch(url), "Alpha Vantage");
  if (data.Note || data.Information) throw new Error(data.Note || data.Information);
  const quote = data["Global Quote"];
  if (!quote?.["05. price"]) throw new Error(`No quote was returned for ${symbol}.`);
  return {
    symbol,
    price: Number(quote["05. price"]),
    change: Number(quote["09. change"]),
    changePercent: Number(quote["10. change percent"].replace("%", "")),
    tradingDay: quote["07. latest trading day"],
  };
}

export async function fetchHeadlines(symbols) {
  if (!process.env.SERPA_API_KEY) return [];
  const url = new URL(SERP_URL);
  url.search = new URLSearchParams({
    engine: "google_news",
    q: `${symbols.join(" OR ")} stock market`,
    api_key: process.env.SERPA_API_KEY,
    hl: "en",
    gl: "us",
  });
  const data = await readJson(await fetch(url), "SerpAPI");
  if (data.error) throw new Error(data.error);
  return (data.news_results || []).slice(0, 5).map((item) => ({
    title: item.title,
    source: typeof item.source === "object" ? item.source.name : item.source,
    link: item.link,
  }));
}
