#!/usr/bin/env python3
"""
Fetches VZY bug data from Jira and writes data.json for the dashboard.
Runs via GitHub Actions on a cron schedule.
"""

import os
import json
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

# Config from environment variables (GitHub Secrets)
JIRA_DOMAIN = os.environ.get('JIRA_DOMAIN', 'hbeindia.atlassian.net')
JIRA_EMAIL = os.environ.get('JIRA_EMAIL', '')
JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN', '')
PROJECT_KEY = os.environ.get('JIRA_PROJECT_KEY', 'VZY')

PLATFORMS = ['ANDROID', 'ATV', 'CMS Adaptor', 'CMS Dashboard', 'DishIT', 'IOS', 'LG_TV', 'SAM_TV', 'WEB']
STATUSES = ['OPEN', 'IN PROGRESS', 'REOPENED', 'IN REVIEW', 'ISSUE ACCEPTED', 'PARKED']

def fetch_jira_data():
    """Fetch bug data from Jira Cloud REST API v3 (new /search/jql endpoint with cursor pagination)."""
    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    # Fetch ALL issues first (to discover issue types), then filter in code
    jql = f'project = {PROJECT_KEY} ORDER BY updated DESC'

    # New Jira Cloud endpoint (replaces deprecated /rest/api/3/search)
    url = f'https://{JIRA_DOMAIN}/rest/api/3/search/jql'

    all_issues = []
    next_page_token = None

    while True:
        payload = {
            'jql': jql,
            'maxResults': 100,
            'fields': ['*all']
        }
        if next_page_token:
            payload['nextPageToken'] = next_page_token

        response = requests.post(url, headers=headers, auth=auth, json=payload)
        response.raise_for_status()
        data = response.json()

        issues = data.get('issues', [])
        all_issues.extend(issues)

        total = data.get('total', len(all_issues))
        print(f"Fetched {len(all_issues)} of {total} issues...")

        # Cursor-based pagination
        next_page_token = data.get('nextPageToken')
        if not next_page_token or len(issues) == 0:
            break

    print(f"Total issues fetched: {len(all_issues)}")
    return all_issues


def detect_platform(issue):
    """Detect platform from summary, labels, components, and custom fields."""
    fields = issue.get('fields', {})
    labels = [l.upper() for l in fields.get('labels', [])]
    components = [c.get('name', '').upper() for c in fields.get('components', [])]
    summary = (fields.get('summary') or '').upper()

    # Also check ALL custom fields for platform info
    custom_vals = []
    for key, val in fields.items():
        if key.startswith('customfield_') and val:
            if isinstance(val, str):
                custom_vals.append(val.upper())
            elif isinstance(val, dict):
                custom_vals.append((val.get('value', '') or val.get('name', '')).upper())
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        custom_vals.append(item.upper())
                    elif isinstance(item, dict):
                        custom_vals.append((item.get('value', '') or item.get('name', '')).upper())

    all_text = ' '.join(labels + components + custom_vals + [summary])

    # Platform detection patterns (order matters - more specific first)
    platform_patterns = {
        'CMS Adaptor': ['CMS ADAPTOR', 'CMS_ADAPTOR', 'CMSADAPTOR'],
        'CMS Dashboard': ['CMS DASHBOARD', 'CMS_DASHBOARD', 'CMSDASHBOARD'],
        'DishIT': ['DISHIT', 'DISH IT', 'DISH_IT'],
        'LG_TV': ['LG_TV', 'LGTV', 'LG TV', 'WEBOS', 'LG-TV'],
        'SAM_TV': ['SAM_TV', 'SAMTV', 'SAM TV', 'SAMSUNG TV', 'SAMSUNG_TV', 'TIZEN', 'SAM-TV'],
        'ATV': ['ATV', 'ANDROID TV', 'ANDROID_TV', 'ANDROIDTV', 'FIRE TV', 'FIRETV', 'FIRE_TV'],
        'ANDROID': ['ANDROID'],
        'IOS': ['IOS', 'APPLE', 'IPHONE', 'IPAD'],
        'WEB': ['WEB'],
    }

    for platform, patterns in platform_patterns.items():
        for pattern in patterns:
            if pattern in all_text:
                return platform

    return None


def build_dashboard_data(issues):
    """Build the platform x status matrix."""
    # Initialize matrix
    matrix = {}
    for p in PLATFORMS:
        matrix[p] = {s: 0 for s in STATUSES}

    # Tracking counters
    total_bugs = 0
    matched_counted = 0
    unmatched_platforms = 0
    unmatched_status = 0
    bug_status_breakdown = {}

    for issue in issues:
        fields = issue.get('fields', {})
        status_name = fields.get('status', {}).get('name', '')
        issue_type = fields.get('issuetype', {}).get('name', '')

        platform = detect_platform(issue)
        status_upper = status_name.upper()

        # Only count bugs
        if issue_type.upper() == 'BUG':
            total_bugs += 1
            # Track all bug statuses
            bug_status_breakdown[status_name] = bug_status_breakdown.get(status_name, 0) + 1

            if platform and status_upper in STATUSES:
                matrix[platform][status_upper] += 1
                matched_counted += 1
            elif platform and status_upper not in STATUSES:
                unmatched_status += 1
            elif not platform:
                unmatched_platforms += 1

    # Print summary
    print(f"\n=== FETCH SUMMARY ===")
    print(f"Total issues: {len(issues)}")
    print(f"Total bugs: {total_bugs}")
    print(f"Matched & counted: {matched_counted}")
    print(f"Platform matched but status not tracked: {unmatched_status}")
    print(f"Platform unmatched: {unmatched_platforms}")
    print(f"Bug statuses: {bug_status_breakdown}")
    print(f"=====================\n")

    return matrix


def main():
    if not JIRA_EMAIL or not JIRA_API_TOKEN:
        print("ERROR: JIRA_EMAIL and JIRA_API_TOKEN environment variables required.")
        print("Set these as GitHub Secrets.")
        exit(1)

    print(f"Fetching data from {JIRA_DOMAIN} for project {PROJECT_KEY}...")
    issues = fetch_jira_data()
    matrix = build_dashboard_data(issues)

    output = {
        'data': matrix,
        'updated_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'total_issues_fetched': len(issues),
        'project': PROJECT_KEY
    }

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json')
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Written to {output_path}")
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
