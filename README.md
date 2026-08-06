# Northstar Market Recap

A deployable MERN application whose first feature is an AI-assisted daily market recap.

## Stack

- React + Vite client
- Node.js + Express API
- MongoDB + Mongoose for optional recap persistence
- Alpha Vantage for quotes, SerpAPI for headlines, and OpenAI for the written recap

## Local setup

1. Install Node.js 20 or newer.
2. From the project folder, install dependencies:

   ```powershell
   npm install
   npm run install:all
   ```

3. Copy your existing `.env` values into `server/.env`. Use `server/.env.example` as the template. `MONGODB_URI` is optional for local development.
4. Run both applications:

   ```powershell
   npm run dev
   ```

5. Open `http://localhost:5173`.

## API

`GET /api/recap?symbols=SPY,QQQ,DIA`

The API accepts up to five tickers. Successful results are cached for five minutes to conserve third-party API quotas. API keys are never sent to the browser.

## Deployment

Deploy `client` to a static host such as Vercel and `server` to a Node host such as Render, Railway, or Fly.io. Set the server environment variables in the host dashboard, configure `CLIENT_ORIGIN` to the deployed client URL, and set the client's API routing or proxy to the deployed server URL.
