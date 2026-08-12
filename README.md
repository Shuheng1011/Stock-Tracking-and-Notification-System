# Autonomous Traders

## Run locally

### 1. Open the project

```powershell
cd "C:\Users\Shuhe\Documents\Stock Project"
```

### 2. Create and activate the Python environment

```powershell
uv venv .venv --python 3.12.12
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Install the frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

### 4. Add API keys

Create a `.env` file in the project root:

```dotenv
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key

# Optional: the app uses simulated prices without this key
MASSIVE_API_KEY=your_massive_api_key

RUN_EVERY_N_MINUTES=60
RUN_EVEN_WHEN_MARKET_IS_CLOSED=false
USE_MANY_MODELS=false
```

### 5. Start the backend

Open a terminal in the project root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.api:app --reload --port 8000
```

### 6. Start the frontend

Open a second terminal:

```powershell
cd "C:\Users\Shuhe\Documents\Stock Project\frontend"
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### 7. Start the autonomous traders

Open a third terminal in the project root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m backend.trading_floor
```

To run the traders while the market is closed, change this value in `.env` and restart the trading process:

```dotenv
RUN_EVEN_WHEN_MARKET_IS_CLOSED=true
```
