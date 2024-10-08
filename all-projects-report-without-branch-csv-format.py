import requests
import csv
from datetime import datetime
from collections import defaultdict
import argparse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# GitLab API configuration
# Use environment variable for the GitLab instance URL if self-hosted.
# Default GitLab URL if not set as environment variable
GITLAB_URL = os.environ.get("GITLAB_URL", "https://gitlab.com")

PRIVATE_TOKEN = os.environ.get("GITLAB_TOKEN")  # Use environment variable for the token
if not PRIVATE_TOKEN:
    raise ValueError("GITLAB_TOKEN environment variable must be set. export GITLAB_TOKEN=your_gitlab_token_here")
HEADERS = {"Private-Token": PRIVATE_TOKEN}


def get_all_projects():
    print(f"Fetching projects from {GITLAB_URL}")
    projects = []
    page = 1
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
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


def fetch_project_branches(project):
    project_id = project['id']
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
    return project, branches


def fetch_commits(project, branch, start_date, end_date):
    project_id = project['id']
    branch_name = branch['name']
    commits = []
    page = 1
    while True:
        response = requests.get(
            f"{GITLAB_URL}/api/v4/projects/{project_id}/repository/commits",
            params={
                "ref_name": branch_name,
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
            print(f"Error fetching commits for project {project_id}, branch {branch_name}: {response.status_code}")
            break
    return project, branch_name, commits


def generate_authors_report(start_date, end_date):
    projects = get_all_projects()
    all_authors = defaultdict(
        lambda: defaultdict(lambda: {"commit_count": 0, "project_url": "", "dates": set(), "commit_ids": set()}))

    with ThreadPoolExecutor(max_workers=20) as executor:
        branch_futures = {executor.submit(fetch_project_branches, project): project for project in projects}

        for future in as_completed(branch_futures):
            project, branches = future.result()
            project_id = project['id']
            project_name = project['name']
            project_url = project['web_url']

            commit_futures = {executor.submit(fetch_commits, project, branch, start_date, end_date): branch for branch
                              in branches}

            for commit_future in as_completed(commit_futures):
                project, branch_name, commits = commit_future.result()

                for commit in commits:
                    author = commit['author_name']
                    commit_id = commit['id']
                    commit_date = datetime.strptime(commit['created_at'], "%Y-%m-%dT%H:%M:%S.%f%z").date()

                    # Check if commit is already counted for this author and project
                    if commit_id not in all_authors[author][project_name]["commit_ids"]:
                        all_authors[author][project_name]["commit_count"] += 1
                        all_authors[author][project_name]["project_url"] = project_url
                        all_authors[author][project_name]["dates"].add(commit_date)
                        all_authors[author][project_name]["commit_ids"].add(commit_id)

    generate_authors_csv(all_authors, start_date, end_date)
    return f"Authors report generated for {len(projects)} projects from {start_date.date()} to {end_date.date()}"


def generate_authors_csv(authors, start_date, end_date):
    filename = f'authors_report_{start_date.strftime("%Y-%m-%d")}_{end_date.strftime("%Y-%m-%d")}.csv'
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
