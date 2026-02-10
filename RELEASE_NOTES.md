# Release Notes - VF Bug Health Dashboard v1.0

**Release Date:** February 10, 2026
**Project:** VZY UAT
**Prepared By:** VZY Engineering Team

---

## What's New

### VF Bug Health Dashboard - Leadership Dashboard

We are excited to announce the launch of the **VF Bug Health Dashboard**, a real-time web-based tool that provides instant visibility into bug status across all VZY UAT platforms.

**Access the dashboard:** https://sunilk9898.github.io/vf-bug-dashboard/

---

## Key Features

### Real-Time Bug Tracking
- Live data synced from Jira every 30 minutes
- No manual updates required
- Auto-refreshes in the browser every 5 minutes

### Platform Coverage
All 9 VZY UAT platforms are tracked:
- ANDROID, ATV, CMS Adaptor, CMS Dashboard, DishIT, IOS, LG_TV, SAM_TV, WEB

### Bug Status Tracking
6 active statuses monitored:
- OPEN, IN PROGRESS, REOPENED, IN REVIEW, ISSUE ACCEPTED, PARKED

### Dashboard Views
- **Summary Cards** - Quick glance at total issues and status counts
- **Status Distribution** - Color-coded breakdown across all platforms
- **Platform Bar Chart** - Visual comparison of bug count per platform
- **Platform x Status Table** - Detailed matrix with totals

### Automated Data Pipeline
- GitHub Actions fetches Jira data on a 30-minute schedule
- Zero manual intervention required after initial setup
- Secure: API credentials stored as encrypted GitHub Secrets

---

## Technical Highlights

| Feature | Detail |
|---------|--------|
| Hosting | GitHub Pages (free, HTTPS-enabled) |
| Data Source | Jira Cloud REST API v3 (new `/search/jql` endpoint) |
| Refresh Rate | Every 30 minutes (automated) |
| Authentication | Jira API Token (encrypted in GitHub Secrets) |
| Browser Support | All modern browsers (Chrome, Firefox, Safari, Edge) |
| Mobile Support | Responsive design, works on phones and tablets |

---

## Benefits

1. **Time Savings** - No need to log into Jira and run individual queries
2. **Instant Visibility** - One URL for all stakeholders to check bug health
3. **Always Current** - Data auto-updates every 30 minutes
4. **Zero Cost** - Built on free-tier services (GitHub Pages + GitHub Actions)
5. **No Login Required** - Public URL accessible to anyone with the link
6. **Cross-Platform** - Works on desktop, tablet, and mobile browsers

---

## Known Limitations (v1.0)

- Approximately 57 out of 1815 issues have undetected platforms (bugs without platform keywords in their summary)
- GitHub Actions cron may experience up to 15-minute delay during peak hours
- Dashboard shows bug data only (tasks, stories, and epics are excluded)

---

## Upcoming Enhancements (Planned)

- Historical trend charts (week-over-week comparison)
- Priority breakdown view (Critical, High, Medium, Low)
- Assignee workload distribution
- Email notification for critical bug threshold alerts
- Export to PDF/CSV functionality

---

## How to Access

Simply open this URL in any browser:

**https://sunilk9898.github.io/vf-bug-dashboard/**

No login, no installation, no setup required.

---

## Support

For questions or issues with the dashboard, contact the VZY Engineering Team.
