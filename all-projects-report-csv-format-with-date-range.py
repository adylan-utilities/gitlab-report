import argparse
import csv
import os
from collections import defaultdict
from datetime import datetime

import requests

# GitLab API configuration
GITLAB_URL = os.environ.get("GITLAB_URL")  # Use environment variable for the GitLab instance URL if self-hosted
if not GITLAB_URL:
    GITLAB_URL = "https://gitlab.com"   # Default GitLab URL if not set as environment variable
PRIVATE_TOKEN = os.environ.get("GITLAB_TOKEN")  # Use environment variable for the token
if not PRIVATE_TOKEN:
    raise ValueError("GITLAB_TOKEN environment variable must be set. export GITLAB_TOKEN=your_gitlab_token_here")
HEADERS = {"Private-Token": PRIVATE_TOKEN}


def get_all_projects():
    print(f"Fetching projects from {GITLAB_URL}")
    projects = []
    page = 1
    while True:
        response = requests.get(f"{GITLAB_URL}/api/v4/projects?page={page}&per_page=100", headers=HEADERS)
        if response.status_code == 200:
            batch = response.json()
            if not batch:
                break
            projects.extend(batch)
            page += 1
        else:
            print(f"Error fetching projects: {response.status_code}")
            break
    return projects


def get_project_branches(project_id):
    branches = []
    page = 1
    while True:
        response = requests.get(
            f"{GITLAB_URL}/api/v4/projects/{project_id}/repository/branches?page={page}&per_page=100", headers=HEADERS)
        if response.status_code == 200:
            batch = response.json()
            if not batch:
                break
            branches.extend(batch)
            page += 1
        else:
            print(f"Error fetching branches for project {project_id}: {response.status_code}")
            break
    return branches


def get_commits(project_id, branch, start_date, end_date):
    commits = []
    page = 1
    while True:
        response = requests.get(
            f"{GITLAB_URL}/api/v4/projects/{project_id}/repository/commits",
            params={
                "ref_name": branch,
                "since": start_date.isoformat(),
                "until": end_date.isoformat(),
                "page": page,
                "per_page": 100
            },
            headers=HEADERS
        )
        if response.status_code == 200:
            batch = response.json()
            if not batch:
                break
            commits.extend(batch)
            page += 1
        else:
            print(f"Error fetching commits for project {project_id}, branch {branch}: {response.status_code}")
            break
    return commits


def get_commit_details(project_id, commit_sha):
    response = requests.get(
        f"{GITLAB_URL}/api/v4/projects/{project_id}/repository/commits/{commit_sha}/diff",
        headers=HEADERS
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching commit details for {commit_sha}: {response.status_code}")
        return []


def generate_report(start_date, end_date, report_types):
    projects = get_all_projects()

    all_commits = []
    all_authors = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"count": 0, "project_url": ""})))
    all_files = defaultdict(lambda: {"count": 0, "project_url": ""})

    for project in projects:
        project_id = project['id']
        project_name = project['name']
        project_url = project['web_url']
        branches = get_project_branches(project_id)

        for branch in branches:
            branch_name = branch['name']
            commits = get_commits(project_id, branch_name, start_date, end_date)

            for commit in commits:
                commit['project_name'] = project_name
                commit['branch_name'] = branch_name
                commit['project_url'] = project_url
                all_commits.append(commit)
                all_authors[commit['author_name']][project_name][branch_name]["count"] += 1
                all_authors[commit['author_name']][project_name][branch_name]["project_url"] = project_url
                details = get_commit_details(project_id, commit['id'])
                for file in details:
                    key = f"{project_name}: {branch_name}: {file['new_path']}"
                    all_files[key]["count"] += 1
                    all_files[key]["project_url"] = project_url

    date_str = start_date.strftime("%Y-%m-%d")
    if 'commits' in report_types:
        generate_commits_csv(all_commits, date_str)
    if 'authors' in report_types:
        generate_authors_csv(all_authors, date_str)
    if 'files' in report_types:
        generate_files_csv(all_files, date_str)

    return f"Report generated for {len(projects)} projects from {start_date.date()} to {end_date.date()}"


def generate_commits_csv(commits, date_str):
    filename = f'all_commits_report_{date_str}.csv'
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Project', 'Branch', 'Commit ID', 'Author', 'Date', 'Message', 'Repository Link'])
        for commit in commits:
            writer.writerow([
                commit['project_name'],
                commit['branch_name'],
                commit['short_id'],
                commit['author_name'],
                commit['created_at'],
                commit['title'],
                commit['project_url']
            ])


def generate_authors_csv(authors, date_str):
    filename = f'all_authors_report_{date_str}.csv'
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Author', 'Project', 'Branch', 'Commit Count', 'Date', 'Repository Link'])
        for author, projects in authors.items():
            for project, branches in projects.items():
                for branch, data in branches.items():
                    writer.writerow([author, project, branch, data["count"], date_str, data["project_url"]])


def generate_files_csv(files_changed, date_str):
    filename = f'all_files_report_{date_str}.csv'
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Project: Branch: File Path', 'Change Count', 'Date', 'Repository Link'])
        for file, data in sorted(files_changed.items(), key=lambda x: x[1]["count"], reverse=True):
            writer.writerow([file, data["count"], date_str, data["project_url"]])


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate GitLab commit report for a specified date range.")
    parser.add_argument("start_date", type=parse_date, help="Start date in YYYY-MM-DD format")
    parser.add_argument("end_date", type=parse_date, help="End date in YYYY-MM-DD format")
    parser.add_argument("--reports", nargs='+', choices=['commits', 'authors', 'files'],
                        default=['commits', 'authors', 'files'],
                        help="Specify which reports to generate")
    args = parser.parse_args()

    if args.start_date > args.end_date:
        print("Error: Start date must be before end date.")
    else:
        result = generate_report(args.start_date, args.end_date, args.reports)
        print(result)
