# Claude Code Environment Setup

## Quick Setup (Copy-Paste)

### 1. Python Path

Add to Claude Code settings or run before commands:

```bash
export PYTHONPATH=/home/user/Coinswarm/src:$PYTHONPATH
```

Or create `.clauderc`:

```bash
cat > ~/.clauderc << 'EOF'
export PYTHONPATH=/home/user/Coinswarm/src:$PYTHONPATH
EOF
```

### 2. Environment Variables

```bash
# Copy example config
cp .env.example .env

# Edit with your API keys (all optional, all free)
nano .env

# Or set directly in shell
export WORKER_URL=https://your-worker.workers.dev
export FRED_API_KEY=your_key_here
export CRYPTOCOMPARE_API_KEY=your_key_here
```

### 3. Python Dependencies

```bash
pip install -r requirements.txt
```

Or minimal install:

```bash
pip install httpx ccxt python-dotenv pytrends
```

## Network Configuration

### Issue: External APIs Blocked (403)

**Blocked:**
- ❌ Binance API
- ❌ Google News RSS
- ❌ Most external HTTP requests

**Solution Options:**

#### A. Use Cloudflare Worker (Recommended)

Deploy `DEPLOY_TO_CLOUDFLARE.js` then:

```bash
export WORKER_URL=https://your-worker.workers.dev
```

#### B. Use Mock Data (Works Now)

```bash
python demo_full_backtest.py  # Uses generated data
```

#### C. Use CSV Files

Download from https://data.binance.vision/ then:

```python
from coinswarm.data_ingest.csv_importer import CSVImporter
importer = CSVImporter()
data = importer.import_binance_csv("BTCUSDT-1h-2024-10.csv", "BTC-USDC", "1h")
```

## Run Commands

### Test System (No Setup Required)

```bash
# All 7 agents with mock data
python demo_full_backtest.py
```

### With Real Data (After Worker Deployed)

```bash
# Set Worker URL
export WORKER_URL=https://your-worker.workers.dev

# Run backtest
python demo_real_data.py
```

### Development

```bash
# Run tests
pytest tests/

# Check agent behavior
python -m coinswarm.agents.trend_agent

# Run continuous backtester
python -m coinswarm.backtesting.continuous_backtester
```

## Recommended Claude Code Settings

Create `.claude/config.json`:

```json
{
  "python": {
    "pythonPath": "/usr/bin/python3",
    "extraPaths": [
      "${workspaceFolder}/src"
    ]
  },
  "environment": {
    "PYTHONPATH": "${workspaceFolder}/src"
  }
}
```

## Troubleshooting

### "No module named 'coinswarm'"

```bash
export PYTHONPATH=/home/user/Coinswarm/src:$PYTHONPATH
# Or
pip install -e .
```

### "403 Forbidden" from APIs

Use Cloudflare Worker or CSV files (see above)

### "Division by zero" errors

Normal - RiskManager needs price history. Errors will stop after a few ticks.

## That's It!

Run this to verify setup:

```bash
python demo_full_backtest.py
```

You should see agents voting and trades executing!
<!-- Cleared: Content moved to Development_strategies.md -->
