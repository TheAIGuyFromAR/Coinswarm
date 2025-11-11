# Deployment Free Tier

This document explains how to deploy Coinswarm using only free-tier resources on Cloudflare and other platforms.

## 1. Cloudflare Free Tier
- Up to 100k requests/day
- 10ms CPU time per request
- 1GB storage per D1 database

## 2. Recommendations
- Use paginated data fetching
- Monitor usage limits
- Optimize worker code for CPU/memory

## 3. References
- See `cloudflare-workers-analysis.md`