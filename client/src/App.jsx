import { useEffect, useState } from "react";

const money = (value) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);

export default function App() {
  const [symbols, setSymbols] = useState("SPY, QQQ, DIA");
  const [recap, setRecap] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadRecap() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/recap?symbols=${encodeURIComponent(symbols)}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Unable to load the recap.");
      setRecap(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadRecap(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <main>
      <nav><div className="brand"><span>✦</span> NORTHSTAR</div><div className="status"><i /> MARKET INTELLIGENCE</div></nav>
      <header>
        <p className="eyebrow">DAILY BRIEFING</p>
        <h1>The market, distilled.</h1>
        <p className="lede">A focused read on today's movement across the symbols that matter to you.</p>
        <form onSubmit={(event) => { event.preventDefault(); loadRecap(); }}>
          <label htmlFor="symbols">WATCHLIST</label>
          <div className="search-row">
            <input id="symbols" value={symbols} onChange={(event) => setSymbols(event.target.value.toUpperCase())} placeholder="SPY, QQQ, DIA" />
            <button disabled={loading}>{loading ? "GENERATING…" : "GENERATE RECAP →"}</button>
          </div>
        </form>
      </header>

      {error && <section className="error">{error}</section>}
      {loading && !recap && <section className="loading">Gathering market signals…</section>}
      {recap && (
        <>
          <section className="ticker-grid">
            {recap.market.map((item) => (
              <article className="ticker" key={item.symbol}>
                <div><strong>{item.symbol}</strong><span>{item.tradingDay}</span></div>
                <h2>{money(item.price)}</h2>
                <p className={item.changePercent >= 0 ? "up" : "down"}>{item.changePercent >= 0 ? "▲" : "▼"} {Math.abs(item.changePercent).toFixed(2)}%</p>
              </article>
            ))}
          </section>

          <section className="content-grid">
            <article className="brief">
              <div className="section-title"><span>01</span><h3>Today's recap</h3></div>
              <div className="summary">{recap.summary}</div>
              <p className="timestamp">Generated {new Date(recap.generatedAt).toLocaleString()}{recap.cached ? " · Cached" : ""}</p>
            </article>
            <aside>
              <div className="section-title"><span>02</span><h3>In the news</h3></div>
              {recap.headlines.length ? recap.headlines.map((story) => (
                <a className="headline" href={story.link} target="_blank" rel="noreferrer" key={story.link}>
                  <small>{story.source || "MARKET NEWS"}</small><p>{story.title}</p><b>↗</b>
                </a>
              )) : <p className="muted">No headlines available.</p>}
            </aside>
          </section>
          {!!recap.warnings?.length && <details><summary>Data notices</summary>{recap.warnings.map((warning) => <p key={warning}>{warning}</p>)}</details>}
        </>
      )}
      <footer>Market data may be delayed. For informational purposes only.</footer>
    </main>
  );
}
