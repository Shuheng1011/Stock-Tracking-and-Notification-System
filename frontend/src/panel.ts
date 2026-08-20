// One trader's quadrant: header with value and profit, chart, heatmap, log.

import { summarizeTrader, type LogRow } from "./api";
import { PortfolioChart } from "./chart";
import { Heatmap } from "./heatmap";
import { LogView } from "./log";
import type { TraderState } from "./state";
import { TransactionsView } from "./transactions";

export class TraderPanel {
  readonly root: HTMLElement;
  private state: TraderState;
  private chart: PortfolioChart | null = null;
  private heatmap: Heatmap;
  private log: LogView;
  private transactions: TransactionsView;
  private valueEl: HTMLElement;
  private pnlEl: HTMLElement;
  private strategyEl: HTMLElement;
  private summaryButton: HTMLButtonElement;
  private summaryEl: HTMLElement;

  constructor(state: TraderState) {
    this.state = state;
    const { name, model_name, lastname } = state.info;
    this.root = document.createElement("section");
    this.root.className = "panel";
    this.root.innerHTML = `
      <header class="panel-head">
        <span class="panel-name"></span>
        <span class="panel-sub"></span>
        <span class="panel-value" data-trend="flat">$0</span>
        <span class="panel-pnl"></span>
        <span class="panel-strategy"></span>
        <div class="panel-summary">
          <button class="summary-button" type="button">Summarize portfolio</button>
          <div class="summary-output" role="status" aria-live="polite" hidden></div>
        </div>
      </header>
      <div class="panel-chart"></div>
      <div class="panel-heatmap"></div>
      <div class="panel-bottom">
        <div class="panel-col">
          <span class="panel-col-label">Activity</span>
          <div class="panel-log"></div>
        </div>
        <div class="panel-col">
          <span class="panel-col-label">Recent trades</span>
          <div class="panel-transactions"></div>
        </div>
      </div>
    `;
    this.root.querySelector(".panel-name")!.textContent = name;
    this.root.querySelector(".panel-sub")!.textContent = `${model_name} · ${lastname}`;
    this.valueEl = this.root.querySelector(".panel-value")!;
    this.pnlEl = this.root.querySelector(".panel-pnl")!;
    this.strategyEl = this.root.querySelector(".panel-strategy")!;
    this.summaryButton = this.root.querySelector(".summary-button")!;
    this.summaryEl = this.root.querySelector(".summary-output")!;
    this.summaryButton.addEventListener("click", () => void this.generateSummary());
    this.heatmap = new Heatmap(this.root.querySelector(".panel-heatmap")!);
    this.log = new LogView(this.root.querySelector(".panel-log")!);
    this.transactions = new TransactionsView(this.root.querySelector(".panel-transactions")!);
    // Chart is created in mount(), after the panel is in the DOM, because uPlot misbehaves
    // when its host is not laid out at construction time.
  }

  mount(): void {
    if (this.chart) return;
    this.chart = new PortfolioChart(this.root.querySelector(".panel-chart") as HTMLElement);
  }

  update(): void {
    const detail = this.state.detail;
    if (detail) {
      const trend = detail.pnl >= 0 ? "up" : "down";
      this.valueEl.textContent = formatMoney(detail.portfolio_value);
      this.valueEl.dataset.trend = trend;
      this.pnlEl.dataset.trend = trend;
      this.pnlEl.textContent = formatPnl(detail.pnl);
      this.heatmap.render(detail.holdings, this.state.priceDirections());
      this.state.rememberPrices();
      const strategy = detail.strategy.trim();
      this.strategyEl.textContent = strategy || "No strategy set yet";
      this.strategyEl.title = strategy;
      this.strategyEl.classList.toggle("empty", !strategy);
      this.transactions.render(detail.transactions);
    }
    this.chart?.update(this.state.chart);
  }

  renderLogs(rows: LogRow[]): void {
    this.log.render(rows);
  }

  setLeader(isLeader: boolean): void {
    if (isLeader) this.root.dataset.leader = "true";
    else delete this.root.dataset.leader;
  }

  private async generateSummary(): Promise<void> {
    const name = this.state.info.name;
    this.summaryButton.disabled = true;
    this.summaryButton.textContent = "Generating…";
    this.summaryEl.hidden = false;
    this.summaryEl.dataset.state = "loading";
    this.summaryEl.textContent = "Reviewing portfolio…";

    try {
      const result = await summarizeTrader(name);
      const generated = new Date(result.generated_at).toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit",
      });
      this.summaryEl.dataset.state = "success";
      this.summaryEl.textContent = result.summary;
      this.summaryEl.title = `${result.cached ? "Cached" : "Generated"} at ${generated}`;
      this.summaryButton.textContent = "Refresh summary";
    } catch (error) {
      console.error(`summary failed for ${name}`, error);
      this.summaryEl.dataset.state = "error";
      this.summaryEl.textContent = error instanceof Error
        ? error.message
        : "The portfolio summary is temporarily unavailable.";
      this.summaryButton.textContent = "Try again";
    } finally {
      this.summaryButton.disabled = false;
    }
  }
}

function formatMoney(n: number): string {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

function formatPnl(n: number): string {
  const sign = n >= 0 ? "+" : "-";
  return `${sign}${Math.abs(n).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 })}`;
}
