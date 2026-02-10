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
    """Fetch bug data from Jira REST API (supports both v2 and v3)."""
    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)

    # Build JQL - fetch all bugs in active statuses
    status_list = ', '.join([f'"{s}"' for s in STATUSES])
    jql = f'project = {PROJECT_KEY} AND type = Bug AND status in ({status_list}) ORDER BY updated DESC'

    all_issues = []
    start_at = 0

    # Try REST API v2 first (more widely supported), fall back to v3 POST
    api_versions = [
        ('v2_get', f'https://{JIRA_DOMAIN}/rest/api/2/search'),
        ('v3_post', f'https://{JIRA_DOMAIN}/rest/api/3/search/jql'),
    ]

    chosen_url = None
    chosen_method = None

    for method, url in api_versions:
        try:
            if 'get' in method:
                test_resp = requests.get(url, headers={'Accept': 'application/json'}, auth=auth,
                    params={'jql': jql, 'startAt': 0, 'maxResults': 1, 'fields': 'status'})
            else:
                test_resp = requests.post(url, headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
                    auth=auth, json={'jql': jql, 'startAt': 0, 'maxResults': 1, 'fields': ['status']})

            if test_resp.status_code == 200:
                chosen_url = url
                chosen_method = method
                print(f"Using API: {method} ({url})")
                break
            else:
                print(f"API {method} returned {test_resp.status_code}, trying next...")
        except Exception as e:
            print(f"API {method} failed: {e}, trying next...")

    if not chosen_url:
        raise Exception("Could not connect to any Jira API endpoint")

    while True:
        if 'get' in chosen_method:
            params = {
                'jql': jql,
                'startAt': start_at,
                'maxResults': 100,
                'fields': 'status,labels,components,summary,priority,assignee,updated'
            }
            response = requests.get(chosen_url, headers={'Accept': 'application/json'}, auth=auth, params=params)
        else:
            payload = {
                'jql': jql,
                'startAt': start_at,
                'maxResults': 100,
                'fields': ['status', 'labels', 'components', 'summary', 'priority', 'assignee', 'updated']
            }
            response = requests.post(chosen_url,
                headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
                auth=auth, json=payload)

        response.raise_for_status()
        data = response.json()

        issues = data.get('issues', [])
        all_issues.extend(issues)

        total = data.get('total', 0)
        print(f"Fetched {len(all_issues)} of {total} issues...")

        if len(all_issues) >= total or len(issues) == 0:
            break
        start_at += 100

    print(f"Total issues fetched: {len(all_issues)}")
    return all_issues


def detect_platform(issue):
    """Detect platform from labels and components."""
    labels = [l.upper() for l in issue.get('fields', {}).get('labels', [])]
    components = [c.get('name', '').upper() for c in issue.get('fields', {}).get('components', [])]
    all_text = ' '.join(labels + components)

    for platform in PLATFORMS:
        if platform.upper() in all_text:
            return platform

    # Fuzzy matching for common variations
    mappings = {
        'ANDROID_MOBILE': 'ANDROID', 'ANDROID MOBILE': 'ANDROID',
        'APPLE_TV': 'ATV', 'APPLE TV': 'ATV', 'ANDROID_TV': 'ATV', 'ANDROID TV': 'ATV',
        'CMS_ADAPTOR': 'CMS Adaptor', 'CMS_DASHBOARD': 'CMS Dashboard',
        'SAMSUNG': 'SAM_TV', 'SAMSUNG_TV': 'SAM_TV', 'SAMSUNG TV': 'SAM_TV',
        'LG': 'LG_TV', 'LGTV': 'LG_TV', 'LG TV': 'LG_TV',
        'DISH': 'DishIT', 'DISHIT': 'DishIT',
    }
    for key, val in mappings.items():
        if key in all_text:
            return val

    return None


def build_dashboard_data(issues):
    """Build the platform x status matrix."""
    # Initialize matrix
    matrix = {}
    for p in PLATFORMS:
        matrix[p] = {s: 0 for s in STATUSES}

    for issue in issues:
        status_name = issue.get('fields', {}).get('status', {}).get('name', '').upper()
        platform = detect_platform(issue)

        if platform and status_name in STATUSES:
            matrix[platform][status_name] += 1

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
