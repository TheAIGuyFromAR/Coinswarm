"""
Backtesting Engine

Replays historical market data to test trading strategies.

Key features:
- Fast replay of historical data (>1000x real-time speed)
- Multiple timeframes (1m, 5m, 1h, 1d)
- Realistic order execution (slippage, fees)
- Position tracking and P&L calculation
- Performance metrics (Sharpe ratio, max drawdown, win rate)

Use cases:
1. Test new strategies before production
2. Validate evolved strategies from StrategyLearningAgent
3. Research academic strategies from AcademicResearchAgent
4. Optimize agent parameters
5. Keep compute >50% utilized between live trades
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

from coinswarm.data_ingest.base import DataPoint
from coinswarm.agents.committee import AgentCommittee, CommitteeDecision


logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Backtest configuration"""
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000.0
    symbols: List[str] = None
    timeframe: str = "1m"  # 1m, 5m, 15m, 1h, 4h, 1d
    commission: float = 0.001  # 0.1% per trade
    slippage: float = 0.0005  # 0.05% slippage
    max_positions: int = 5


@dataclass
class BacktestTrade:
    """Trade in backtest"""
    id: str
    symbol: str
    action: str
    entry_time: datetime
    entry_price: float
    size: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission_paid: float = 0.0
    reason: str = ""
    agent_votes: Optional[Dict] = None


@dataclass
class BacktestResult:
    """Results from a backtest"""
    strategy_id: str
    start_date: datetime
    end_date: datetime
    duration_days: float

    # Capital and returns
    initial_capital: float
    final_capital: float
    total_return: float  # Absolute return in USD
    total_return_pct: float  # Percentage return

    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float

    # P&L metrics
    total_pnl: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    profit_factor: float  # Total wins / total losses

    # Risk metrics
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float  # Return / max drawdown

    # Time metrics
    avg_trade_duration: float  # Seconds
    max_trade_duration: float

    # Trades
    trades: List[BacktestTrade]


class BacktestEngine:
    """
    Backtesting engine for strategy validation.

    Process:
    1. Load historical data
    2. Replay data tick-by-tick
    3. Run agent committee at each tick
    4. Execute trades in simulation
    5. Track positions and P&L
    6. Calculate performance metrics

    Speed: Can replay 1 month of 1m data in ~10-30 seconds
    """

    def __init__(self, config: BacktestConfig):
        self.config = config

        # Simulation state
        self.current_time: Optional[datetime] = None
        self.capital = config.initial_capital
        self.initial_capital = config.initial_capital

        # Positions
        self.positions: Dict[str, BacktestTrade] = {}

        # Completed trades
        self.trades: List[BacktestTrade] = []

        # Equity curve (for drawdown calculation)
        self.equity_curve: List[Tuple[datetime, float]] = []

        # Statistics
        self.stats = {
            "ticks_processed": 0,
            "trades_executed": 0,
            "orders_rejected": 0
        }

    async def run_backtest(
        self,
        committee: AgentCommittee,
        historical_data: Dict[str, List[DataPoint]]
    ) -> BacktestResult:
        """
        Run backtest with given committee and historical data.

        Args:
            committee: Agent committee to test
            historical_data: Dict mapping symbol → list of DataPoints

        Returns:
            BacktestResult with performance metrics
        """

        logger.info(
            f"Starting backtest: {self.config.start_date} to {self.config.end_date}, "
            f"symbols={self.config.symbols}, capital=${self.capital:,.0f}"
        )

        start_time = datetime.now()

        # Merge and sort all data points by timestamp
        all_ticks = self._merge_and_sort_data(historical_data)

        logger.info(f"Loaded {len(all_ticks)} ticks for replay")

        # Replay data tick-by-tick
        for tick in all_ticks:
            await self._process_tick(tick, committee)

        # Close all open positions at end
        for symbol in list(self.positions.keys()):
            final_price = all_ticks[-1].data.get("price", 0)
            await self._close_position(symbol, final_price, "backtest_end")

        # Calculate final metrics
        result = self._calculate_results()

        duration = (datetime.now() - start_time).total_seconds()
        speedup = (self.config.end_date - self.config.start_date).total_seconds() / duration

        logger.info(
            f"Backtest complete: {result.total_trades} trades, "
            f"return={result.total_return_pct:+.2%}, "
            f"win_rate={result.win_rate:.1%}, "
            f"sharpe={result.sharpe_ratio:.2f}, "
            f"time={duration:.1f}s ({speedup:.0f}x real-time)"
        )

        return result

    def _merge_and_sort_data(
        self,
        historical_data: Dict[str, List[DataPoint]]
    ) -> List[DataPoint]:
        """Merge all symbols and sort by timestamp"""

        all_ticks = []
        for symbol, ticks in historical_data.items():
            all_ticks.extend(ticks)

        # Sort by timestamp
        all_ticks.sort(key=lambda t: t.timestamp)

        return all_ticks

    async def _process_tick(
        self,
        tick: DataPoint,
        committee: AgentCommittee
    ):
        """Process a single tick"""

        self.current_time = tick.timestamp
        self.stats["ticks_processed"] += 1

        symbol = tick.symbol
        price = tick.data.get("price", 0)

        # Update equity curve
        current_equity = self._calculate_current_equity(tick)
        self.equity_curve.append((self.current_time, current_equity))

        # Check open positions for stop loss / take profit
        if symbol in self.positions:
            position = self.positions[symbol]

            # Check stop loss (placeholder - would use HedgeAgent in production)
            stop_loss_pct = 0.02
            take_profit_pct = 0.06

            if position.action == "BUY":
                # Long position
                pnl_pct = (price - position.entry_price) / position.entry_price

                if pnl_pct <= -stop_loss_pct:
                    # Stop loss triggered
                    await self._close_position(symbol, price, "stop_loss")
                    return

                if pnl_pct >= take_profit_pct:
                    # Take profit triggered
                    await self._close_position(symbol, price, "take_profit")
                    return

        # Get committee decision
        position = self.positions.get(symbol)
        market_context = {
            "account_value": current_equity,
            "position": position,
            "backtest_mode": True
        }

        decision = await committee.vote(tick, position, market_context)

        # Execute decision if confidence is high enough
        if decision.confidence >= committee.confidence_threshold:
            if decision.action == "BUY" and symbol not in self.positions:
                await self._open_position(symbol, "BUY", price, decision)
            elif decision.action == "SELL" and symbol in self.positions:
                await self._close_position(symbol, price, "agent_signal")

    async def _open_position(
        self,
        symbol: str,
        action: str,
        price: float,
        decision: CommitteeDecision
    ):
        """Open a new position"""

        # Check if we can open more positions
        if len(self.positions) >= self.config.max_positions:
            self.stats["orders_rejected"] += 1
            return

        # Calculate size based on available capital
        position_capital = self.capital * 0.1  # 10% per position
        size = position_capital / price

        # Apply slippage
        entry_price = price * (1 + self.config.slippage)

        # Calculate commission
        commission = position_capital * self.config.commission

        # Check if we have enough capital
        cost = (size * entry_price) + commission
        if cost > self.capital:
            self.stats["orders_rejected"] += 1
            return

        # Deduct from capital
        self.capital -= cost

        # Create trade
        trade = BacktestTrade(
            id=f"{symbol}_{self.current_time.timestamp()}",
            symbol=symbol,
            action=action,
            entry_time=self.current_time,
            entry_price=entry_price,
            size=size,
            commission_paid=commission,
            reason=decision.reason,
            agent_votes=decision.votes
        )

        self.positions[symbol] = trade
        self.stats["trades_executed"] += 1

        logger.debug(
            f"OPEN {action} {size:.4f} {symbol} @ ${entry_price:.2f} "
            f"(commission=${commission:.2f})"
        )

    async def _close_position(
        self,
        symbol: str,
        price: float,
        reason: str
    ):
        """Close an open position"""

        if symbol not in self.positions:
            return

        position = self.positions[symbol]

        # Apply slippage
        exit_price = price * (1 - self.config.slippage)

        # Calculate P&L
        if position.action == "BUY":
            pnl = (exit_price - position.entry_price) * position.size
            pnl_pct = (exit_price - position.entry_price) / position.entry_price
        else:
            pnl = (position.entry_price - exit_price) * position.size
            pnl_pct = (position.entry_price - exit_price) / position.entry_price

        # Calculate commission
        exit_value = position.size * exit_price
        commission = exit_value * self.config.commission

        # Net P&L after commissions
        net_pnl = pnl - commission - position.commission_paid

        # Add to capital
        self.capital += exit_value - commission

        # Update trade
        position.exit_time = self.current_time
        position.exit_price = exit_price
        position.pnl = net_pnl
        position.pnl_pct = pnl_pct
        position.commission_paid += commission

        # Move to completed trades
        self.trades.append(position)
        del self.positions[symbol]

        logger.debug(
            f"CLOSE {position.action} {position.size:.4f} {symbol} @ ${exit_price:.2f} "
            f"P&L=${net_pnl:+.2f} ({pnl_pct:+.2%}) [{reason}]"
        )

    def _calculate_current_equity(self, tick: DataPoint) -> float:
        """Calculate current account equity (cash + positions)"""

        equity = self.capital

        # Add unrealized P&L from open positions
        symbol = tick.symbol
        price = tick.data.get("price", 0)

        if symbol in self.positions:
            position = self.positions[symbol]

            if position.action == "BUY":
                unrealized_pnl = (price - position.entry_price) * position.size
            else:
                unrealized_pnl = (position.entry_price - price) * position.size

            equity += unrealized_pnl

        return equity

    def _calculate_results(self) -> BacktestResult:
        """Calculate final backtest results"""

        # Basic stats
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        # P&L metrics
        total_pnl = sum(t.pnl for t in self.trades)
        avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
        largest_win = max((t.pnl for t in self.trades), default=0)
        largest_loss = min((t.pnl for t in self.trades), default=0)

        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        # Returns
        final_capital = self.capital
        total_return = final_capital - self.initial_capital
        total_return_pct = total_return / self.initial_capital

        # Drawdown
        max_drawdown, max_drawdown_pct = self._calculate_max_drawdown()

        # Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio()

        # Sortino ratio (like Sharpe but only considers downside volatility)
        sortino_ratio = self._calculate_sortino_ratio()

        # Calmar ratio
        calmar_ratio = total_return_pct / abs(max_drawdown_pct) if max_drawdown_pct != 0 else 0

        # Time metrics
        durations = [
            (t.exit_time - t.entry_time).total_seconds()
            for t in self.trades
            if t.exit_time
        ]
        avg_trade_duration = sum(durations) / len(durations) if durations else 0
        max_trade_duration = max(durations) if durations else 0

        # Duration
        duration_days = (self.config.end_date - self.config.start_date).total_seconds() / 86400

        return BacktestResult(
            strategy_id="backtest",
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            duration_days=duration_days,
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            avg_trade_duration=avg_trade_duration,
            max_trade_duration=max_trade_duration,
            trades=self.trades
        )

    def _calculate_max_drawdown(self) -> Tuple[float, float]:
        """Calculate maximum drawdown"""

        if not self.equity_curve:
            return 0.0, 0.0

        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        peak = self.equity_curve[0][1]

        for timestamp, equity in self.equity_curve:
            if equity > peak:
                peak = equity

            drawdown = peak - equity
            drawdown_pct = drawdown / peak if peak > 0 else 0

            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct

        return max_drawdown, max_drawdown_pct

    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio (risk-adjusted return)"""

        if not self.trades:
            return 0.0

        # Calculate returns for each trade
        returns = [t.pnl_pct for t in self.trades]

        # Mean and std dev
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return 0.0

        # Annualize (assume 365 trading days)
        annual_return = mean_return * 365
        annual_std_dev = std_dev * (365 ** 0.5)

        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe = annual_return / annual_std_dev

        return sharpe

    def _calculate_sortino_ratio(self) -> float:
        """Calculate Sortino ratio (downside risk-adjusted return)"""

        if not self.trades:
            return 0.0

        # Calculate returns
        returns = [t.pnl_pct for t in self.trades]
        mean_return = sum(returns) / len(returns)

        # Only consider downside deviation (negative returns)
        downside_returns = [r for r in returns if r < 0]

        if not downside_returns:
            return float('inf')  # No downside!

        downside_variance = sum(r ** 2 for r in downside_returns) / len(downside_returns)
        downside_std_dev = downside_variance ** 0.5

        if downside_std_dev == 0:
            return 0.0

        # Annualize
        annual_return = mean_return * 365
        annual_downside_std_dev = downside_std_dev * (365 ** 0.5)

        sortino = annual_return / annual_downside_std_dev

        return sortino
