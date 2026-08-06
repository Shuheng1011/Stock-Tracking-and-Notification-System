import dotenv from "dotenv";
import cors from "cors";
import express from "express";
import mongoose from "mongoose";
import recapRouter from "./routes/recap.js";

// Load server/.env in deployment, then fall back to the repository-level .env locally.
dotenv.config();
dotenv.config({ path: new URL("../../.env", import.meta.url), override: false });

const app = express();
const port = process.env.PORT || 5000;

app.use(cors({ origin: process.env.CLIENT_ORIGIN || "http://localhost:5173" }));
app.use(express.json());
app.get("/api/health", (_req, res) => res.json({ status: "ok" }));
app.use("/api/recap", recapRouter);
app.use((error, _req, res, _next) => {
  console.error(error);
  res.status(500).json({ message: error.message || "Unable to generate the recap." });
});

if (process.env.MONGODB_URI) {
  mongoose.connect(process.env.MONGODB_URI).then(() => console.log("MongoDB connected")).catch((error) => console.warn("MongoDB unavailable:", error.message));
} else {
  console.log("MONGODB_URI not set; recaps will not be persisted.");
}

app.listen(port, () => console.log(`API listening on http://localhost:${port}`));
