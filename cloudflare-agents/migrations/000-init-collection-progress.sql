-- Initialize collection_progress table with 15 tokens
-- Run this before starting data collection crons

INSERT OR IGNORE INTO collection_progress (
  symbol, coin_id,
  total_minutes, total_days, total_hours,
  daily_status, minute_status, hourly_status,
  minutes_collected, days_collected, hours_collected,
  error_count
) VALUES
  ('BTCUSDT', 'bitcoin', 2628000, 1825, 43800, 'pending', 'pending', 'pending', 0, 0, 0, 0),
  ('ETHUSDT', 'ethereum', 2628000, 1825, 43800, 'pending', 'pending', 'pending', 0, 0, 0, 0),
  ('SOLUSDT', 'solana', 2628000, 1825, 43800, 'pending', 'pending', 'pending', 0, 0, 0, 0),
  ('BNBUSDT', 'binancecoin', 2628000, 1825, 43800, 'pending', 'pending', 'pending', 0, 0, 0, 0),
  ('CAKEUSDT', 'pancakeswap-token', 2628000, 1825, 43800, 'pending', 'pending', 'pending', 0, 0, 0, 0),
  ('RAYUSDT', 'raydium', 2628000, 1825, 43800, 'pending', 'pending', 'pending', 0, 0, 0, 0),
  ('ORCAUSDT', 'orca', 2628000, 1825, 43800, 'pending', 'pending', 'pending', 0, 0, 0, 0),
  ('JUPUSDT', 'jupiter-exchange-solana', 2628000, 1825, 43800, 'pending', 'pending', 'pending', 0, 0, 0, 0),
  ('ARBUSDT', 'arbitrum', 2628000, 1825, 43800, 'pending', 'pending', 'pending', 0, 0, 0, 0),
  ('GMXUSDT', 'gmx', 2628000, 1825, 43800, 'pending', 'pending', 'pending', 0, 0, 0, 0),
  ('OPUSDT', 'optimism', 2628000, 1825, 43800, 'pending', 'pending', 'pending', 0, 0, 0, 0),
  ('VELOUSDT', 'velodrome-finance', 2628000, 1825, 43800, 'pending', 'pending', 'pending', 0, 0, 0, 0),
  ('MATICUSDT', 'matic-network', 2628000, 1825, 43800, 'pending', 'pending', 'pending', 0, 0, 0, 0),
  ('QUICKUSDT', 'quickswap', 2628000, 1825, 43800, 'pending', 'pending', 'pending', 0, 0, 0, 0),
  ('AEROUSDT', 'aerodrome-finance', 2628000, 1825, 43800, 'pending', 'pending', 'pending', 0, 0, 0, 0);

-- Totals explanation:
-- 5 years of data for each token
-- total_minutes: 365 days * 24 hours * 60 minutes * 5 years = 2,628,000 minutes
-- total_days: 365 days * 5 years = 1,825 days
-- total_hours: 365 days * 24 hours * 5 years = 43,800 hours
