# Coinswarm Development Guide

This guide covers setting up the development environment and running Coinswarm locally.

## Prerequisites

- **Python 3.11+** installed
- **Docker** and **Docker Compose** installed
- **Git** installed
- API keys for Coinbase and Alpaca (sandbox/paper trading accounts)

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/TheAIGuyFromAR/Coinswarm.git
cd Coinswarm

# Initialize development environment (installs dependencies and starts Docker services)
make init
```

This will:
- Install Python dependencies
- Create `.env` from `.env.example`
- Start all Docker services (Redis, NATS, PostgreSQL, etc.)

### 2. Configure API Keys

Edit `.env` and add your API credentials:

```bash
# Coinbase API (get from https://www.coinbase.com/settings/api)
COINBASE_API_KEY=your_coinbase_key_here
COINBASE_API_SECRET=your_coinbase_secret_here
COINBASE_ENVIRONMENT=sandbox  # Use sandbox for development

# Alpaca API (get from https://alpaca.markets)
ALPACA_API_KEY=your_alpaca_key_here
ALPACA_API_SECRET=your_alpaca_secret_here
ALPACA_ENVIRONMENT=paper  # Use paper trading for development
```

### 3. Verify Services

Check that all Docker services are running:

```bash
docker-compose ps
```

You should see:
- `coinswarm-redis` - Vector database (port 6379)
- `coinswarm-nats` - Message bus (port 4222)
- `coinswarm-postgres` - Relational database (port 5432)
- `coinswarm-influxdb` - Time-series database (port 8086)
- `coinswarm-mongodb` - Document storage (port 27017)
- `coinswarm-prometheus` - Metrics (port 9090)
- `coinswarm-grafana` - Dashboards (port 3001)

### 4. Run Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/unit/test_coinbase_client.py -v

# Run with coverage
pytest --cov=src/coinswarm --cov-report=html
```

### 5. Run MCP Server

```bash
# Run Coinbase MCP server
make run-mcp

# Or directly with Python
python -m src.coinswarm.mcp_server.server
```

The MCP server will start and listen for connections via stdio.

## Project Structure

```
Coinswarm/
├── src/coinswarm/           # Main package
│   ├── api/                 # API clients (Coinbase, Alpaca)
│   ├── mcp_server/          # MCP server implementation
│   ├── agents/              # Trading agents
│   ├── memory/              # Quorum memory system
│   ├── core/                # Core utilities (config, logging)
│   └── utils/               # Helper utilities
├── tests/                   # Test suite
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
├── docs/                    # Documentation
│   ├── architecture/        # Architecture specs
│   ├── agents/              # Agent documentation
│   ├── api/                 # API integration docs
│   └── patterns/            # Pattern learning docs
├── config/                  # Configuration files
│   └── prometheus.yml       # Prometheus config
├── scripts/                 # Utility scripts
│   └── init-db.sql          # PostgreSQL initialization
├── docker-compose.yml       # Docker services
├── pyproject.toml           # Python package config
├── Makefile                 # Development commands
└── .env.example             # Environment template
```

## Development Workflow

### Making Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and add tests

3. Format code:
   ```bash
   make format
   ```

4. Run linters:
   ```bash
   make lint
   ```

5. Run tests:
   ```bash
   make test
   ```

6. Commit and push:
   ```bash
   git add .
   git commit -m "Add your feature"
   git push origin feature/your-feature-name
   ```

### Code Style

We use:
- **Black** for code formatting (100 char line length)
- **Ruff** for fast linting
- **MyPy** for type checking

Run all formatters and linters:
```bash
make format
make lint
```

## Docker Services

### Starting Services

```bash
# Start all services
make docker-up

# Start specific service
docker-compose up -d redis
```

### Stopping Services

```bash
# Stop all services
make docker-down

# Stop specific service
docker-compose stop redis
```

### Viewing Logs

```bash
# All services
make docker-logs

# Specific service
docker-compose logs -f redis
```

### Service URLs

- **Redis**: `localhost:6379`
- **RedisInsight**: `http://localhost:8001` (Redis GUI)
- **NATS**: `localhost:4222`
- **NATS Monitoring**: `http://localhost:8222`
- **PostgreSQL**: `localhost:5432`
- **InfluxDB**: `http://localhost:8086`
- **MongoDB**: `localhost:27017`
- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3001` (admin/coinswarm_dev)

## Database Management

### PostgreSQL

```bash
# Connect to PostgreSQL
docker exec -it coinswarm-postgres psql -U coinswarm -d coinswarm

# View tables
\dt

# Query trades
SELECT * FROM trades LIMIT 10;
```

### Redis

```bash
# Connect to Redis CLI
docker exec -it coinswarm-redis redis-cli

# Check keys
KEYS *

# View vector index info
FT.INFO episodic_memory_idx
```

### InfluxDB

Access at `http://localhost:8086`
- Username: `admin`
- Password: `coinswarm_dev` (or your configured password)
- Organization: `coinswarm`
- Bucket: `market_data`

## Testing MCP Server

### Using MCP Inspector

```bash
# Install MCP inspector (if not already installed)
npm install -g @anthropic-ai/mcp-inspector

# Run MCP server with inspector
mcp-inspector python -m src.coinswarm.mcp_server.server
```

### Testing Tools

Example MCP tool calls:

```json
{
  "name": "get_market_data",
  "arguments": {
    "product_id": "BTC-USD"
  }
}
```

```json
{
  "name": "place_market_order",
  "arguments": {
    "product_id": "BTC-USD",
    "side": "BUY",
    "quote_size": "10.00"
  }
}
```

## Monitoring

### Prometheus

Access at `http://localhost:9090`

Example queries:
- `coinswarm_trades_total` - Total trades
- `coinswarm_agent_pnl` - Agent P&L
- `rate(coinswarm_api_requests_total[5m])` - API request rate

### Grafana

Access at `http://localhost:3001`
- Username: `admin`
- Password: `coinswarm_dev`

Pre-configured dashboards will be added in `config/grafana/dashboards/`

## Common Issues

### Issue: Docker services won't start

**Solution**: Ensure Docker is running and ports are not in use
```bash
# Check if ports are in use
lsof -i :6379  # Redis
lsof -i :4222  # NATS
lsof -i :5432  # PostgreSQL

# Kill processes if needed
kill -9 <PID>
```

### Issue: Python import errors

**Solution**: Ensure package is installed in editable mode
```bash
pip install -e .
```

### Issue: API authentication errors

**Solution**: Verify API keys in `.env`
```bash
# Check your Coinbase API key is valid
curl -X GET https://api.coinbase.com/api/v3/brokerage/accounts \
  -H "CB-ACCESS-KEY: your_key" \
  -H "CB-ACCESS-SIGN: signature" \
  -H "CB-ACCESS-TIMESTAMP: timestamp"
```

### Issue: Redis vector search not working

**Solution**: Ensure RediSearch module is loaded
```bash
# Check loaded modules
docker exec -it coinswarm-redis redis-cli MODULE LIST

# Should see "search" module
```

## Next Steps

1. **Run paper trading**: Implement basic trading strategy
2. **Add more agents**: Create domain-specific agents (trend, mean-reversion, etc.)
3. **Implement memory system**: Build quorum-governed memory
4. **Add monitoring**: Create Grafana dashboards
5. **Pattern learning**: Implement pattern extraction and optimization

## Resources

- [Project Documentation](docs/README.md)
- [Coinbase API Docs](docs/api/coinbase-api-integration.md)
- [Multi-Agent Architecture](docs/agents/multi-agent-architecture.md)
- [Quorum Memory System](docs/architecture/quorum-memory-system.md)
- [Hierarchical Decision System](docs/architecture/hierarchical-temporal-decision-system.md)

## Getting Help

- Check the [documentation](docs/README.md)
- Review [architecture diagrams](docs/architecture/)
- Look at [example code](tests/)
- Open an issue on GitHub

---

**Happy Trading! 🚀**
