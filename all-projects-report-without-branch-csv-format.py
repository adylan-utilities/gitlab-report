import requests
import csv
from datetime import datetime
from collections import defaultdict
import argparse
import os

# GitLab API configuration
GITLAB_URL = os.environ.get("GITLAB_URL")  # Use environment variable for the GitLab instance URL if self-hosted
if not GITLAB_URL:
    GITLAB_URL = "https://gitlab.com"  # Default GitLab URL if not set as environment variable
    print(f"Set GitLab instance URL if self-hosted. export GITLAB_URL=your_gitlab_instance_url")
PRIVATE_TOKEN = os.environ.get("GITLAB_TOKEN")  # Use environment variable for the token
if not PRIVATE_TOKEN:
    raise ValueError("GITLAB_TOKEN environment variable must be set. export GITLAB_TOKEN=your_gitlab_token_here")
HEADERS = {"Private-Token": PRIVATE_TOKEN}


def get_all_projects():
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


def generate_authors_report(start_date, end_date):
    projects = get_all_projects()
    all_authors = defaultdict(lambda: defaultdict(lambda: {"commit_count": 0, "project_url": "", "dates": set()}))

    for project in projects:
        project_id = project['id']
        project_name = project['name']
        project_url = project['web_url']
        branches = get_project_branches(project_id)

        for branch in branches:
            branch_name = branch['name']
            commits = get_commits(project_id, branch_name, start_date, end_date)

            for commit in commits:
                author = commit['author_name']
                commit_date = datetime.strptime(commit['created_at'], "%Y-%m-%dT%H:%M:%S.%f%z").date()
                all_authors[author][project_name]["commit_count"] += 1
                all_authors[author][project_name]["project_url"] = project_url
                all_authors[author][project_name]["dates"].add(commit_date)

    generate_authors_csv(all_authors, start_date, end_date)
    return f"Authors report generated for {len(projects)} projects from {start_date.date()} to {end_date.date()}"


def generate_authors_csv(authors, start_date, end_date):
    filename = f'authors_report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.csv'
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Author', 'Project', 'Commit Count', 'Dates', 'Repository Link'])
        for author, projects in authors.items():
            for project, data in projects.items():
                writer.writerow([
                    author,
                    project,
                    data["commit_count"],
                    ', '.join(str(date) for date in sorted(data["dates"])),
                    data["project_url"]
                ])


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate GitLab authors report for a specified date range.")
    parser.add_argument("start_date", type=parse_date, help="Start date in YYYY-MM-DD format")
    parser.add_argument("end_date", type=parse_date, help="End date in YYYY-MM-DD format")
    args = parser.parse_args()

    if args.start_date > args.end_date:
        print("Error: Start date must be before end date.")
    else:
        result = generate_authors_report(args.start_date, args.end_date)
        print(result)
