# Coinswarm Evolution Dashboards

Beautiful, interactive dashboards for monitoring the multi-agent competitive evolution trading system.

## 🎨 Dashboards

### 1. Architecture Dashboard (`architecture.html`)
**Visual representation of the 3-layer system**

- **Layer 1: Pattern Discovery** - Chaos, Academic, Technical agents
- **Layer 2: Reasoning Agents** - Self-reflective trading agents
- **Layer 3: Meta-Learning** - Model research and optimization
- Self-improvement loop diagram
- Real-time system statistics

### 2. Pattern Leaderboard (`patterns.html`)
**Top trading patterns ranked by performance**

- Filter by origin (chaos/academic/technical)
- Filter by status (winning/testing)
- Minimum runs filter
- Win rate, H2H records, votes
- Progress bars showing performance
- Real-time stats (total, winning, by origin)

### 3. Agent Swarm (`swarm.html`)
**Live view of all agents in the population**

- Visual card grid of all agents
- Personality types and generations
- Fitness scores with progress bars
- Active/Eliminated status filtering
- Trade stats and competition wins
- Lineage indicators (original vs evolved)

### 4. Agent Leaderboard (`agents.html`)
**Ranking of agents by fitness score**

- Sort by fitness, ROI, win rate, or trades
- Detailed agent statistics
- Competition records
- Expandable rows with full details
- Top 100 active agents
- Generation tracking

## 🚀 Quick Start

### Option 1: Local HTTP Server (Quickest)

```bash
cd cloudflare-agents/dashboards
python3 -m http.server 8000
```

Then visit: `http://localhost:8000/architecture.html`

### Option 2: GitHub Pages

1. Create a new branch for GitHub Pages:
```bash
git checkout -b gh-pages
```

2. Copy dashboard files to root:
```bash
cp cloudflare-agents/dashboards/*.html .
```

3. Commit and push:
```bash
git add *.html
git commit -m "Add dashboards for GitHub Pages"
git push origin gh-pages
```

4. Enable GitHub Pages in repository settings pointing to `gh-pages` branch

5. Access at: `https://yourusername.github.io/Coinswarm/architecture.html`

### Option 3: Cloudflare Pages

1. Go to Cloudflare Dashboard → Pages
2. Create new project from GitHub
3. Set build directory to `cloudflare-agents/dashboards`
4. Deploy!

Your dashboards will be available at: `https://your-project.pages.dev`

## 🔧 Configuration

### Update API Endpoints

If your Cloudflare Worker is NOT at the same domain as your dashboards, update the API URLs in each HTML file:

```javascript
// Change this:
const response = await fetch('/api/stats');

// To this (replace with your worker URL):
const response = await fetch('https://your-worker.workers.dev/api/stats');
```

Search for `/api/` in each file and replace with your full worker URL.

## 📡 API Endpoints

All dashboards use these API endpoints from the Cloudflare Worker:

| Endpoint | Description | Parameters |
|----------|-------------|------------|
| `/api/stats` | System statistics | None |
| `/api/patterns` | Pattern data | `?origin=all&status=all&min_runs=3&limit=50` |
| `/api/agents/all` | All agents | None |
| `/api/agents/leaderboard` | Top agents | None |

### Example API Calls

```bash
# Get system stats
curl https://your-worker.workers.dev/api/stats

# Get patterns filtered
curl "https://your-worker.workers.dev/api/patterns?origin=academic&limit=100"

# Get agent leaderboard
curl https://your-worker.workers.dev/api/agents/leaderboard
```

## 🎯 Features

### Auto-Refresh
All dashboards auto-refresh data every 30 seconds to show live updates.

### Responsive Design
Works on desktop, tablet, and mobile devices.

### Modern UI
- Gradient backgrounds
- Smooth animations
- Card-based layouts
- Interactive filters
- Progress visualizations

### Performance
- Lightweight (no frameworks)
- Fast loading
- Minimal JavaScript
- Efficient API calls

## 🛠️ Customization

### Change Colors

Find the gradient definition in each file's CSS:

```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### Change Refresh Rate

Find this in each file's JavaScript:

```javascript
setInterval(fetchData, 30000); // 30 seconds
```

Change `30000` to your desired milliseconds.

### Add Custom Metrics

1. Add new API endpoint in `evolution-agent-simple.ts`
2. Add HTML element in dashboard
3. Add JavaScript to fetch and display data

## 📊 Example Screenshots

### Architecture Dashboard
Shows the complete 3-layer system with agent flow and statistics.

### Pattern Leaderboard
```
Rank | Pattern              | Origin    | Votes | Win Rate | H2H Record
1    | Momentum Breakout    | ACADEMIC  | 45    | 78.3%    | 23W-6L
2    | Volume Spike         | TECHNICAL | 38    | 71.2%    | 19W-8L
3    | Mean Reversion       | ACADEMIC  | 42    | 69.8%    | 18W-9L
```

### Agent Swarm
Grid of agent cards showing personality, generation, fitness, and stats.

### Agent Leaderboard
```
Rank | Agent                    | Gen | Fitness | Win Rate | Avg ROI
1    | AGGRESSIVE-GEN3-742      | 3   | 78.4    | 72.1%    | 3.24%
2    | MOMENTUM_HUNTER-GEN4-123 | 4   | 76.2    | 68.9%    | 3.11%
3    | BALANCED-GEN2-891        | 2   | 74.8    | 65.4%    | 2.98%
```

## 🐛 Troubleshooting

### Dashboard shows "Loading..." forever

**Problem**: Can't connect to API endpoints

**Solution**:
1. Check that worker is deployed and running
2. Verify API endpoint URLs in HTML files
3. Check CORS settings if hosted on different domain
4. Open browser console to see errors

### Data shows all zeros or dashes

**Problem**: Database tables don't exist yet or are empty

**Solution**:
1. Run database migrations
2. Wait for first agent competition (Cycle 900)
3. Check worker logs for errors

### Styling looks broken

**Problem**: CSS not loading properly

**Solution**:
1. View page source and check CSS is present
2. Clear browser cache
3. Try different browser

## 📝 Development

### Local Development

1. Run local HTTP server (see Quick Start)
2. Update API URLs to point to your dev worker
3. Edit HTML files
4. Refresh browser to see changes

### Testing

Test each API endpoint manually:

```bash
curl https://your-worker.workers.dev/api/stats | jq
curl https://your-worker.workers.dev/api/patterns | jq
curl https://your-worker.workers.dev/api/agents/leaderboard | jq
```

## 🔐 Security

These are **read-only** dashboards - they only display data, never modify it.

However:
- Keep your worker URL private if desired
- Consider adding authentication for production
- Use Cloudflare Access for private dashboards

## 📚 Learn More

- [Cloudflare Pages Docs](https://developers.cloudflare.com/pages/)
- [GitHub Pages Docs](https://pages.github.com/)
- [Cloudflare Workers Docs](https://developers.cloudflare.com/workers/)

## 💡 Tips

1. **Bookmark your dashboards** for quick access
2. **Use browser split view** to monitor multiple dashboards
3. **Set dashboards as browser start pages** for always-on monitoring
4. **Share dashboard URLs** with team members
5. **Screenshot interesting moments** in agent evolution

---

*Created with ❤️ for the Coinswarm Evolution System*
