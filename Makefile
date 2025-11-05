.PHONY: help install dev-install test lint format clean docker-up docker-down docker-logs init

help:
	@echo "Coinswarm Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install production dependencies"
	@echo "  make dev-install    Install development dependencies"
	@echo "  make init          Initialize development environment"
	@echo ""
	@echo "Development:"
	@echo "  make test          Run tests"
	@echo "  make lint          Run linters"
	@echo "  make format        Format code with black and ruff"
	@echo "  make clean         Clean build artifacts"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up     Start all services"
	@echo "  make docker-down   Stop all services"
	@echo "  make docker-logs   View service logs"
	@echo ""
	@echo "Server:"
	@echo "  make run-mcp       Run MCP server"
	@echo "  make run-agents    Run agent system"

install:
	pip install -e .

dev-install:
	pip install -e ".[dev,test]"

test:
	pytest tests/ -v --cov=src/coinswarm --cov-report=term-missing

lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/
	ruff check --fix src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf build/ dist/

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-restart:
	docker-compose restart

init: dev-install
	@echo "Creating .env file from template..."
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@echo "Starting Docker services..."
	@make docker-up
	@echo ""
	@echo "Development environment initialized!"
	@echo "Edit .env with your API keys before running services."

run-mcp:
	python -m src.coinswarm.mcp_server.server

run-agents:
	python -m src.coinswarm.agents.orchestrator
