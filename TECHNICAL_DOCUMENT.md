# VF Bug Health Dashboard - Technical Document

**Document Version:** 1.0
**Date:** February 10, 2026
**Author:** VZY Engineering Team
**Status:** Production

---

## 1. Overview

The VF Bug Health Dashboard is an automated, real-time web dashboard that visualizes bug status across all VZY UAT platforms. It replaces the manual process of checking Jira tickets individually by providing a single, always-updated view accessible via a public URL.

**Dashboard URL:** https://sunilk9898.github.io/vf-bug-dashboard/

---

## 2. Architecture

```
+------------------+       +-------------------+       +------------------+
|   Jira Cloud     |       | GitHub Actions    |       | GitHub Pages     |
|   (VF Project)   | ----> | (Cron: every 30m) | ----> | (Static Hosting) |
|   REST API v3    |       | fetch_jira.py     |       | index.html       |
+------------------+       +-------------------+       +------------------+
                                    |                          |
                                    v                          v
                              data.json                  User Browser
                           (auto-committed)            (loads data.json)
```

### Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Data Source | Jira Cloud REST API v3 | Source of truth for all bug data |
| Data Fetcher | Python 3.12 (`fetch_jira.py`) | Fetches, filters, and transforms Jira data |
| Scheduler | GitHub Actions (cron) | Runs fetcher every 30 minutes |
| Data Store | `data.json` (Git-tracked) | JSON file with platform x status matrix |
| Frontend | Static HTML/CSS/JS (`index.html`) | Dashboard UI, reads from data.json |
| Hosting | GitHub Pages | Free, HTTPS-enabled static hosting |

---

## 3. Data Flow

### 3.1 Fetch Cycle (Every 30 Minutes)

1. GitHub Actions triggers `.github/workflows/fetch-jira.yml`
2. Python script authenticates with Jira using API token (stored as GitHub Secret)
3. Fetches ALL issues from project `VF` via `POST /rest/api/3/search/jql`
4. Uses cursor-based pagination (`nextPageToken`) to retrieve all 1800+ issues
5. Filters for issue type `Bug` only
6. Detects platform from issue summary, labels, components, and custom fields
7. Builds a platform x status matrix
8. Writes `data.json` with timestamp
9. Auto-commits and pushes to `main` branch
10. GitHub Pages auto-deploys the updated site

### 3.2 Dashboard Load (User Access)

1. User opens dashboard URL
2. Browser fetches `data.json` (with cache-busting query parameter)
3. JavaScript renders summary cards, charts, and table
4. Auto-refreshes every 5 minutes (client-side)
5. Falls back to static data if `data.json` is unavailable

---

## 4. API Integration

### Jira Endpoint
- **URL:** `https://hbeindia.atlassian.net/rest/api/3/search/jql`
- **Method:** POST
- **Authentication:** HTTP Basic Auth (email + API token)
- **Pagination:** Cursor-based (`nextPageToken`)

### JQL Query
```
project = VF ORDER BY updated DESC
```

### Fields Fetched
- `status` - Bug status (Open, In Progress, Reopened, etc.)
- `issuetype` - To filter only Bugs
- `labels`, `components` - Platform detection
- `summary` - Platform detection fallback
- Custom fields - Additional platform metadata

---

## 5. Platform Detection

Platforms are detected from issue data using pattern matching:

| Platform | Detection Patterns |
|----------|-------------------|
| ANDROID | "ANDROID" in summary/labels/custom fields |
| ATV | "ATV", "ANDROID TV", "FIRE TV" |
| CMS Adaptor | "CMS ADAPTOR" |
| CMS Dashboard | "CMS DASHBOARD" |
| DishIT | "DISHIT", "DISH IT" |
| IOS | "IOS", "APPLE", "IPHONE", "IPAD" |
| LG_TV | "LG_TV", "LGTV", "WEBOS" |
| SAM_TV | "SAM_TV", "SAMSUNG TV", "TIZEN" |
| WEB | "WEB" |

Detection order is specific-to-general to avoid mismatches (e.g., "CMS Adaptor" is checked before "ANDROID" to prevent false matches).

---

## 6. Tracked Statuses

| Status | Description |
|--------|-------------|
| OPEN | Newly reported, not yet picked up |
| IN PROGRESS | Currently being worked on |
| REOPENED | Previously resolved, reopened |
| IN REVIEW | Under code/QA review |
| ISSUE ACCEPTED | Accepted as valid issue |
| PARKED | Deferred / on hold |

---

## 7. File Structure

```
vf-bug-dashboard/
  index.html                    # Dashboard frontend
  data.json                     # Auto-generated Jira data (committed by bot)
  fetch_jira.py                 # Python script to fetch Jira data
  .github/
    workflows/
      deploy.yml                # GitHub Pages deployment workflow
      fetch-jira.yml            # Cron job to fetch Jira data every 30 min
```

---

## 8. Security

| Aspect | Implementation |
|--------|---------------|
| API Credentials | Stored as GitHub Secrets (encrypted at rest) |
| Token Exposure | No credentials in source code or HTML |
| Repository | Public (dashboard is view-only, no write access) |
| HTTPS | Enforced by GitHub Pages |
| CORS | Not applicable (data fetched server-side by GitHub Actions) |

### GitHub Secrets Configured
- `JIRA_DOMAIN` - Jira instance domain
- `JIRA_EMAIL` - Service account email
- `JIRA_API_TOKEN` - Jira API token
- `JIRA_PROJECT_KEY` - Project key (VF)

---

## 9. Maintenance

### Updating Platform Detection
Edit `fetch_jira.py` > `platform_patterns` dictionary to add new platform keywords.

### Changing Refresh Frequency
Edit `.github/workflows/fetch-jira.yml` > `cron` expression. Current: `*/30 * * * *` (every 30 min).

### Adding New Statuses
1. Add status to `STATUSES` list in both `fetch_jira.py` and `index.html`
2. Add color mapping in `STATUS_COLORS` and `STATUS_BADGE_CLASS` in `index.html`

### Manual Data Refresh
Go to GitHub > Actions > "Fetch Jira Data" > Run workflow (manual trigger).

---

## 10. Limitations

- Platform detection relies on text patterns; issues without platform keywords in summary/labels will be unmatched (~57 of 1815 issues currently)
- GitHub Actions cron may have up to 15-minute delay on free tier
- Jira API token has an expiration policy; renew in GitHub Secrets when needed
- Free GitHub Pages has soft bandwidth limits (100 GB/month)

---

## 11. Dependencies

| Dependency | Version | Purpose |
|-----------|---------|---------|
| Python | 3.12 | Runtime for fetch script |
| requests | Latest | HTTP client for Jira API |
| GitHub Actions | v4 | CI/CD automation |
| GitHub Pages | - | Static hosting |

---

## 12. Troubleshooting

| Issue | Solution |
|-------|----------|
| Dashboard shows stale data | Check GitHub Actions > "Fetch Jira Data" for failures |
| API 401 error | Regenerate Jira API token, update `JIRA_API_TOKEN` secret |
| API 410 error | Jira deprecated old endpoint; script uses new `/search/jql` |
| 0 issues fetched | Verify `JIRA_PROJECT_KEY` secret matches actual Jira project key |
| Platform counts don't match | Check `detect_platform()` patterns, add missing keywords |
