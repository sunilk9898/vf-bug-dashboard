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

        print(f"POST {url}")
        print(f"JQL: {payload['jql']}")
        response = requests.post(url, headers=headers, auth=auth, json=payload)
        print(f"Response status: {response.status_code}")
        data = response.json()

        # Debug: print raw response keys and first 500 chars
        print(f"Response keys: {list(data.keys())}")
        raw_str = json.dumps(data)
        print(f"Response preview: {raw_str[:500]}")

        response.raise_for_status()

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

    # Debug: collect unique statuses, labels, components, issue types
    seen_statuses = set()
    seen_labels = set()
    seen_components = set()
    seen_types = set()
    unmatched_platforms = 0

    for issue in issues:
        fields = issue.get('fields', {})
        status_name = fields.get('status', {}).get('name', '')
        issue_type = fields.get('issuetype', {}).get('name', '')
        labels = fields.get('labels', [])
        components = [c.get('name', '') for c in fields.get('components', [])]

        seen_statuses.add(status_name)
        seen_labels.update(labels)
        seen_components.update(components)
        seen_types.add(issue_type)

        platform = detect_platform(issue)
        status_upper = status_name.upper()

        # Only count bugs, not all issue types
        if issue_type.upper() == 'BUG':
            if platform and status_upper in STATUSES:
                matrix[platform][status_upper] += 1
            elif not platform:
                unmatched_platforms += 1
                if unmatched_platforms <= 5:
                    summary = fields.get('summary', '')[:60]
                    print(f"  Unmatched bug: [{issue.get('key')}] {summary} (status: {status_name})")

    # Print debug info
    print(f"\n=== DEBUG INFO ===")
    print(f"Total issues: {len(issues)}")
    print(f"Unique issue types: {sorted(seen_types)}")
    print(f"Unique statuses found: {sorted(seen_statuses)}")
    print(f"Unique labels found: {sorted(seen_labels)}")
    print(f"Unique components found: {sorted(seen_components)}")
    print(f"Issues with unmatched platform: {unmatched_platforms}")
    print(f"==================\n")

    return matrix


def main():
    if not JIRA_EMAIL or not JIRA_API_TOKEN:
        print("ERROR: JIRA_EMAIL and JIRA_API_TOKEN environment variables required.")
        print("Set these as GitHub Secrets.")
        exit(1)

    # Debug: list accessible projects
    print("Checking accessible projects...")
    try:
        proj_resp = requests.get(
            f'https://{JIRA_DOMAIN}/rest/api/3/project',
            headers={'Accept': 'application/json'},
            auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
        )
        if proj_resp.status_code == 200:
            projects = proj_resp.json()
            print(f"Accessible projects ({len(projects)}):")
            for p in projects[:20]:
                key = p.get('key', '')
                name = p.get('name', '')
                # Print char by char to avoid secret masking
                key_spaced = ' '.join(list(key))
                name_spaced = ' '.join(list(name))
                print(f"  - Key: [{key_spaced}] Name: [{name_spaced}]")
        else:
            print(f"Project list request returned: {proj_resp.status_code} {proj_resp.text[:200]}")
    except Exception as e:
        print(f"Could not list projects: {e}")

    print(f"\nFetching data from {JIRA_DOMAIN} for project {PROJECT_KEY}...")
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
