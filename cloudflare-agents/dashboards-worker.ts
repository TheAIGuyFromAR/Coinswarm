/**
 * Dashboards Worker
 * Serves static HTML dashboards for the Coinswarm Evolution System
 *
 * Dashboards:
 * - /architecture.html - System architecture visualization
 * - /patterns.html - Pattern leaderboard
 * - /agents.html - Agent leaderboard
 * - /swarm.html - Agent swarm visualization
 */

export default {
  async fetch(request: Request, env: any): Promise<Response> {
    const url = new URL(request.url);

    // Serve static assets from dashboards directory
    // The [assets] configuration in wrangler.toml handles this automatically

    // Root path redirects to architecture dashboard
    if (url.pathname === '/' || url.pathname === '') {
      return Response.redirect(`${url.origin}/architecture.html`, 302);
    }

    // For all other paths, let the assets binding handle it
    // This will serve files from the dashboards/ directory
    return env.ASSETS.fetch(request);
  },
};
