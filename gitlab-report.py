import requests
import csv
from datetime import datetime, timedelta
from collections import defaultdict
import argparse

# GitLab API configuration
GITLAB_URL = "https://gitlab.com"  # Replace with your GitLab instance URL if self-hosted
PRIVATE_TOKEN = "GITLAB_TOKEN"  # Replace with your actual token
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


def generate_report(start_date, end_date):
    projects = get_all_projects()

    all_commits = []
    all_authors = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
    all_files = defaultdict(lambda: defaultdict(int))

    for project in projects:
        project_id = project['id']
        project_name = project['name']
        branches = get_project_branches(project_id)

        for branch in branches:
            branch_name = branch['name']
            commits = get_commits(project_id, branch_name, start_date, end_date)

            for commit in commits:
                commit_date = datetime.strptime(commit['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ").date()
                commit['project_name'] = project_name
                commit['branch_name'] = branch_name
                commit['commit_date'] = commit_date
                all_commits.append(commit)
                all_authors[commit['author_name']][project_name][branch_name][commit_date] += 1
                details = get_commit_details(project_id, commit['id'])
                for file in details:
                    all_files[f"{project_name}: {branch_name}: {file['new_path']}"][commit_date] += 1

    generate_commits_csv(all_commits)
    generate_authors_csv(all_authors)
    generate_files_csv(all_files)

    if start_date.date() == end_date.date():
        return f"Report generated for {len(projects)} projects on {start_date.date()}"
    else:
        return f"Report generated for {len(projects)} projects from {start_date.date()} to {end_date.date()}"


def generate_commits_csv(commits):
    with open('all_commits_report.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Date', 'Project', 'Branch', 'Commit ID', 'Author', 'Message'])
        for commit in commits:
            writer.writerow([
                commit['commit_date'],
                commit['project_name'],
                commit['branch_name'],
                commit['short_id'],
                commit['author_name'],
                commit['title']
            ])


def generate_authors_csv(authors):
    with open('all_authors_report.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Date', 'Author', 'Project', 'Branch', 'Commit Count'])
        for author, projects in authors.items():
            for project, branches in projects.items():
                for branch, dates in branches.items():
                    for date, count in dates.items():
                        writer.writerow([date, author, project, branch, count])


def generate_files_csv(files_changed):
    with open('all_files_report.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Date', 'Project: Branch: File Path', 'Change Count'])
        for file_path, dates in files_changed.items():
            for date, count in dates.items():
                writer.writerow([date, file_path, count])


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate GitLab commit report for a specified date range.")
    parser.add_argument("start_date", type=parse_date, help="Start date in YYYY-MM-DD format")
    parser.add_argument("end_date", type=parse_date, help="End date in YYYY-MM-DD format")
    args = parser.parse_args()

    if args.start_date > args.end_date:
        print("Error: Start date must be before end date.")
    else:
        result = generate_report(args.start_date, args.end_date)
        print(result)