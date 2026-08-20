// Client for the trading floor HTTP API. All paths are relative; in dev the Vite
// proxy forwards /api to the FastAPI backend, so the browser sees one origin.

export interface TraderInfo {
  name: string;
  lastname: string;
  model_name: string;
}

export interface Holding {
  symbol: string;
  quantity: number;
  price: number;
  avg_cost: number;
  market_value: number;
  unrealized_pnl: number;
}

export interface Transaction {
  symbol: string;
  quantity: number;
  price: number;
  timestamp: string;
  rationale: string;
}

export interface TimePoint {
  datetime: string;
  value: number;
}

// Mirrors the full backend payload; the dashboard renders a subset of these fields.
export interface TraderDetail extends TraderInfo {
  balance: number;
  strategy: string;
  portfolio_value: number;
  pnl: number;
  holdings: Holding[];
  transactions: Transaction[];
  time_series: TimePoint[];
}

export interface LogRow {
  datetime: string;
  type: string;
  message: string;
  color: string;
}

export interface MarketInfo {
  source: "massive" | "simulator";
  is_market_open: boolean;
}

export interface PortfolioSummary {
  summary: string;
  generated_at: string;
  cached: boolean;
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path} failed: ${r.status}`);
  return r.json() as Promise<T>;
}

async function post<T>(path: string): Promise<T> {
  const r = await fetch(path, { method: "POST" });
  if (!r.ok) {
    let message = `${path} failed: ${r.status}`;
    try {
      const body = (await r.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Keep the status-based fallback when the response is not JSON.
    }
    throw new Error(message);
  }
  return r.json() as Promise<T>;
}

export function getTraders(): Promise<TraderInfo[]> {
  return get("/api/traders");
}

export function getTrader(name: string): Promise<TraderDetail> {
  return get(`/api/traders/${encodeURIComponent(name)}`);
}

export function getTraderLogs(name: string, lastN = 13): Promise<LogRow[]> {
  return get(`/api/traders/${encodeURIComponent(name)}/logs?last_n=${lastN}`);
}

export function getMarket(): Promise<MarketInfo> {
  return get("/api/market");
}

export function summarizeTrader(name: string): Promise<PortfolioSummary> {
  return post(`/api/traders/${encodeURIComponent(name)}/summary`);
}
