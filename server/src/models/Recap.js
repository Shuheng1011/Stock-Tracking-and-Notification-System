import mongoose from "mongoose";

const marketItemSchema = new mongoose.Schema(
  {
    symbol: { type: String, required: true },
    price: Number,
    change: Number,
    changePercent: Number,
    tradingDay: String,
  },
  { _id: false },
);

const recapSchema = new mongoose.Schema(
  {
    symbols: [{ type: String, required: true }],
    summary: { type: String, required: true },
    market: [marketItemSchema],
    headlines: [{ title: String, source: String, link: String }],
  },
  { timestamps: true },
);

export const Recap = mongoose.model("Recap", recapSchema);
