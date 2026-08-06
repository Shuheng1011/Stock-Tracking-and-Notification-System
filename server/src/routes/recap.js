import { Router } from "express";
import mongoose from "mongoose";
import { Recap } from "../models/Recap.js";
import { fetchHeadlines, fetchQuote } from "../services/marketService.js";
import { createSummary } from "../services/recapService.js";

const router = Router();
const cache = new Map();
const CACHE_MS = 5 * 60 * 1000;

router.get("/", async (req, res, next) => {
  try {
    const raw = String(req.query.symbols || "SPY,QQQ,DIA");
    const symbols = [...new Set(raw.split(",").map((item) => item.trim().toUpperCase()).filter(Boolean))].slice(0, 5);
    if (!symbols.length || symbols.some((symbol) => !/^[A-Z.\-]{1,10}$/.test(symbol))) {
      return res.status(400).json({ message: "Provide valid comma-separated ticker symbols." });
    }

    const cacheKey = symbols.sort().join(",");
    const cached = cache.get(cacheKey);
    if (cached && Date.now() - cached.createdAt < CACHE_MS) return res.json({ ...cached.payload, cached: true });

    const market = [];
    const warnings = [];
    // Sequential calls are intentional because Alpha Vantage free plans are rate limited.
    for (const symbol of symbols) {
      try {
        market.push(await fetchQuote(symbol));
      } catch (error) {
        warnings.push(`${symbol}: ${error.message}`);
      }
    }
    if (!market.length) throw new Error(warnings[0] || "No market data was available.");

    let headlines = [];
    try {
      headlines = await fetchHeadlines(symbols);
    } catch (error) {
      warnings.push(`News: ${error.message}`);
    }
    const summary = await createSummary(market, headlines);
    const payload = { generatedAt: new Date().toISOString(), symbols, market, headlines, summary, warnings };
    cache.set(cacheKey, { createdAt: Date.now(), payload });

    if (mongoose.connection.readyState === 1) {
      await Recap.create(payload).catch((error) => warnings.push(`Database: ${error.message}`));
    }
    res.json(payload);
  } catch (error) {
    next(error);
  }
});

export default router;
