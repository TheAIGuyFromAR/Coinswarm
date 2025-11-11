"""
Memory Persistence - Save/Load Episodes to Cloudflare D1

Backs up in-memory episodes to Cloudflare D1 database for persistence.

Features:
- Periodic auto-backup (every N episodes or every M minutes)
- Load on startup (warm start from previous sessions)
- Prune old episodes (LRU cleanup)
- Compression (reduce storage costs)

Why Cloudflare D1:
- Free tier: 5GB storage, 5M reads/day, 100K writes/day
- Global edge database (<10ms queries)
- Serverless (no infrastructure)
- Perfect for episodic memory backup

Usage:
    persistence = MemoryPersistence(
        worker_url="https://coinswarm.bamn86.workers.dev",
        auto_backup_interval=100  # Backup every 100 episodes
    )

    # Save episodes
    await persistence.backup_episodes(memory.episodes)

    # Load on startup
    episodes = await persistence.load_episodes(max_episodes=1000)
"""

import logging
import json
import gzip
import base64
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import urllib.error

import numpy as np

logger = logging.getLogger(__name__)


class MemoryPersistence:
    """
    Persists memory episodes to Cloudflare D1.

    D1 Schema (uses existing price_data table + new memory_episodes table):

    CREATE TABLE memory_episodes (
        id TEXT PRIMARY KEY,           -- Episode ID
        symbol TEXT NOT NULL,          -- Trading pair
        timestamp INTEGER NOT NULL,    -- Unix timestamp
        action TEXT NOT NULL,          -- BUY/SELL/HOLD
        reward REAL NOT NULL,          -- P&L
        episode_data TEXT NOT NULL,    -- Compressed JSON
        created_at INTEGER
    );
    """

    def __init__(
        self,
        worker_url: str = "https://coinswarm.bamn86.workers.dev",
        auto_backup_interval: int = 100,  # Backup every N episodes
        auto_backup_minutes: int = 30,     # Or every M minutes
        compression: bool = True,          # Compress episode data
        max_episodes_stored: int = 10000   # Prune to this limit
    ):
        self.worker_url = worker_url.rstrip('/')
        self.auto_backup_interval = auto_backup_interval
        self.auto_backup_minutes = auto_backup_minutes
        self.compression = compression
        self.max_episodes_stored = max_episodes_stored

        # Track when to backup
        self.episodes_since_backup = 0
        self.last_backup_time = datetime.now()

        logger.info(
            f"MemoryPersistence initialized: "
            f"backup every {auto_backup_interval} episodes or {auto_backup_minutes} min"
        )

    def should_backup(self) -> bool:
        """Check if it's time to backup"""

        # Backup if interval reached
        if self.episodes_since_backup >= self.auto_backup_interval:
            logger.info(
                f"Auto-backup triggered: {self.episodes_since_backup} episodes since last backup"
            )
            return True

        # Backup if time elapsed
        minutes_elapsed = (datetime.now() - self.last_backup_time).total_seconds() / 60
        if minutes_elapsed >= self.auto_backup_minutes:
            logger.info(
                f"Auto-backup triggered: {minutes_elapsed:.1f} minutes since last backup"
            )
            return True

        return False

    async def backup_episodes(
        self,
        episodes: Dict[str, "Episode"],  # Episode ID -> Episode
        force: bool = False
    ) -> bool:
        """
        Backup episodes to Cloudflare D1.

        Args:
            episodes: Dictionary of episode_id -> Episode
            force: Force backup even if interval not reached

        Returns:
            True if backed up successfully
        """

        if not force and not self.should_backup():
            return False

        logger.info(f"Backing up {len(episodes)} episodes to Cloudflare D1...")

        try:
            # Convert episodes to JSON-serializable format
            serialized_episodes = []

            for episode_id, episode in episodes.items():
                episode_data = self._serialize_episode(episode)

                # Compress if enabled
                if self.compression:
                    episode_json = json.dumps(episode_data)
                    compressed = gzip.compress(episode_json.encode('utf-8'))
                    episode_data_str = base64.b64encode(compressed).decode('ascii')
                else:
                    episode_data_str = json.dumps(episode_data)

                serialized_episodes.append({
                    "id": episode_id,
                    "symbol": episode.symbol,
                    "timestamp": int(episode.timestamp.timestamp()),
                    "action": episode.action,
                    "reward": float(episode.reward),
                    "episode_data": episode_data_str,
                    "compressed": self.compression
                })

            # Send to Worker (batch upsert)
            # Worker endpoint: POST /memory/backup
            url = f"{self.worker_url}/memory/backup"

            payload = json.dumps({
                "episodes": serialized_episodes,
                "max_episodes": self.max_episodes_stored  # Worker will prune old ones
            }).encode('utf-8')

            request = urllib.request.Request(
                url,
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Content-Length': str(len(payload))
                },
                method='POST'
            )

            with urllib.request.urlopen(request, timeout=60) as response:
                result = json.loads(response.read())

                if result.get("success"):
                    backed_up = result.get("backed_up", 0)
                    pruned = result.get("pruned", 0)

                    logger.info(
                        f"✅ Backed up {backed_up} episodes to D1 "
                        f"(pruned {pruned} old episodes)"
                    )

                    # Reset counters
                    self.episodes_since_backup = 0
                    self.last_backup_time = datetime.now()

                    return True
                else:
                    logger.error(f"Backup failed: {result.get('error')}")
                    return False

        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error during backup: {e.code} {e.reason}")
            return False
        except Exception as e:
            logger.error(f"Error backing up episodes: {e}")
            return False

    async def load_episodes(
        self,
        max_episodes: int = 1000,
        symbol: Optional[str] = None,
        since_timestamp: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Load episodes from Cloudflare D1.

        Args:
            max_episodes: Maximum episodes to load
            symbol: Filter by symbol (None = all)
            since_timestamp: Load only episodes after this time

        Returns:
            List of episode dictionaries
        """

        logger.info(f"Loading up to {max_episodes} episodes from D1...")

        try:
            # Build query parameters
            params = {
                "max_episodes": max_episodes
            }

            if symbol:
                params["symbol"] = symbol

            if since_timestamp:
                params["since"] = int(since_timestamp.timestamp())

            # Worker endpoint: GET /memory/load
            url = f"{self.worker_url}/memory/load?{urllib.parse.urlencode(params)}"

            with urllib.request.urlopen(url, timeout=60) as response:
                result = json.loads(response.read())

                if not result.get("success"):
                    logger.error(f"Load failed: {result.get('error')}")
                    return []

                # Deserialize episodes
                episodes = []

                for episode_data in result.get("episodes", []):
                    # Decompress if needed
                    if episode_data.get("compressed"):
                        compressed = base64.b64decode(episode_data["episode_data"])
                        episode_json = gzip.decompress(compressed).decode('utf-8')
                        episode_dict = json.loads(episode_json)
                    else:
                        episode_dict = json.loads(episode_data["episode_data"])

                    episodes.append(episode_dict)

                logger.info(f"✅ Loaded {len(episodes)} episodes from D1")

                return episodes

        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.info("No episodes found in D1 (fresh start)")
                return []
            else:
                logger.error(f"HTTP error loading episodes: {e.code} {e.reason}")
                return []
        except Exception as e:
            logger.error(f"Error loading episodes: {e}")
            return []

    def increment_episode_counter(self):
        """Call after storing each new episode"""
        self.episodes_since_backup += 1

    def _serialize_episode(self, episode) -> Dict:
        """
        Convert Episode object to JSON-serializable dict.

        Args:
            episode: Episode dataclass instance

        Returns:
            Dictionary with all episode data
        """

        return {
            "action": episode.action,
            "symbol": episode.symbol,
            "price": float(episode.price),
            "size": float(episode.size),
            "timestamp": episode.timestamp.isoformat(),

            "confidence": float(episode.confidence),
            "reason": episode.reason,
            "agent_votes": episode.agent_votes,

            # State vector (compress large array)
            "state": episode.state.tolist() if hasattr(episode.state, 'tolist') else [],

            "technical_indicators": episode.technical_indicators,
            "sentiment_data": episode.sentiment_data,
            "market_context": episode.market_context,
            "portfolio_state": episode.portfolio_state,

            "reward": float(episode.reward),
            "holding_period": float(episode.holding_period),
            "exit_reason": episode.exit_reason,
            "exit_price": float(episode.exit_price) if hasattr(episode, 'exit_price') else 0.0,

            "strategy_tags": episode.strategy_tags,
            "regime": episode.regime
        }

    @staticmethod
    def deserialize_episode(episode_dict: Dict, episode_class):
        """
        Convert dict back to Episode object.

        Args:
            episode_dict: Dictionary from _serialize_episode
            episode_class: Episode dataclass to instantiate

        Returns:
            Episode instance
        """

        # Convert state back to numpy array
        if "state" in episode_dict and episode_dict["state"]:
            episode_dict["state"] = np.array(episode_dict["state"])
        else:
            episode_dict["state"] = np.array([])

        # Convert timestamp back to datetime
        if isinstance(episode_dict.get("timestamp"), str):
            episode_dict["timestamp"] = datetime.fromisoformat(episode_dict["timestamp"])

        return episode_class(**episode_dict)


# Example D1 Worker endpoint handlers (JavaScript)
"""
// cloudflare-workers/memory-backup-handler.js

// POST /memory/backup - Store episodes
async function handleMemoryBackup(request, env) {
    const { episodes, max_episodes } = await request.json();

    // Batch insert episodes
    const stmt = env.DB.prepare(
        `INSERT OR REPLACE INTO memory_episodes
         (id, symbol, timestamp, action, reward, episode_data, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)`
    );

    const batch = [];
    for (const ep of episodes) {
        batch.push(
            stmt.bind(
                ep.id,
                ep.symbol,
                ep.timestamp,
                ep.action,
                ep.reward,
                ep.episode_data,
                Math.floor(Date.now() / 1000)
            )
        );
    }

    await env.DB.batch(batch);

    // Prune old episodes (keep only max_episodes)
    await env.DB.prepare(
        `DELETE FROM memory_episodes
         WHERE id NOT IN (
             SELECT id FROM memory_episodes
             ORDER BY timestamp DESC
             LIMIT ?
         )`
    ).bind(max_episodes).run();

    return {
        success: true,
        backed_up: episodes.length,
        pruned: 0  // Calculate actual number pruned
    };
}

// GET /memory/load - Load episodes
async function handleMemoryLoad(request, env) {
    const url = new URL(request.url);
    const max_episodes = parseInt(url.searchParams.get('max_episodes') || '1000');
    const symbol = url.searchParams.get('symbol');
    const since = url.searchParams.get('since');

    let query = `SELECT * FROM memory_episodes`;
    const conditions = [];
    const bindings = [];

    if (symbol) {
        conditions.push('symbol = ?');
        bindings.push(symbol);
    }

    if (since) {
        conditions.push('timestamp >= ?');
        bindings.push(parseInt(since));
    }

    if (conditions.length > 0) {
        query += ` WHERE ` + conditions.join(' AND ');
    }

    query += ` ORDER BY timestamp DESC LIMIT ?`;
    bindings.push(max_episodes);

    const { results } = await env.DB.prepare(query).bind(...bindings).all();

    return {
        success: true,
        episodes: results,
        count: results.length
    };
}
"""
