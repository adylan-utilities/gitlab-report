import requests
import csv
from datetime import datetime, timedelta
from collections import defaultdict

# GitLab API configuration
GITLAB_URL = "https://gitlab.com"  # Replace with your GitLab instance URL if self-hosted
PRIVATE_TOKEN = "GITLAB_TOKEN"  # Replace with your actual token
HEADERS = {"Private-Token": PRIVATE_TOKEN}

# Specific project configuration
PROJECT_ID = "GITLAB_PROJECT_ID"  # Replace with the ID or path of your specific project


def get_project_info():
    response = requests.get(f"{GITLAB_URL}/api/v4/projects/{PROJECT_ID}", headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching project info: {response.status_code}")
        return None


def get_commits(since_date):
    commits = []
    page = 1
    while True:
        response = requests.get(
            f"{GITLAB_URL}/api/v4/projects/{PROJECT_ID}/repository/commits",
            params={"since": since_date, "page": page, "per_page": 100},
            headers=HEADERS
        )
        if response.status_code == 200:
            batch = response.json()
            if not batch:
                break
            commits.extend(batch)
            page += 1
        else:
            print(f"Error fetching commits: {response.status_code}")
            break
    return commits


def get_commit_details(commit_sha):
    response = requests.get(
        f"{GITLAB_URL}/api/v4/projects/{PROJECT_ID}/repository/commits/{commit_sha}/diff",
        headers=HEADERS
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching commit details for {commit_sha}: {response.status_code}")
        return []


def generate_report(days=7):
    since_date = (datetime.now() - timedelta(days=days)).isoformat()
    project = get_project_info()

    if not project:
        return "Failed to fetch project information."

    commits = get_commits(since_date)
    authors = defaultdict(int)
    files_changed = defaultdict(int)

    for commit in commits:
        authors[commit['author_name']] += 1
        details = get_commit_details(commit['id'])
        for file in details:
            files_changed[file['new_path']] += 1

    # Generate CSV files
    generate_commits_csv(commits)
    generate_authors_csv(authors)
    generate_files_csv(files_changed)

    return f"Report generated for project: {project['name']}"


def generate_commits_csv(commits):
    with open('commits_report.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Commit ID', 'Author', 'Date', 'Message'])
        for commit in commits:
            writer.writerow([
                commit['short_id'],
                commit['author_name'],
                commit['created_at'],
                commit['title']
            ])


def generate_authors_csv(authors):
    with open('authors_report.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Author', 'Commit Count'])
        for author, count in sorted(authors.items(), key=lambda x: x[1], reverse=True):
            writer.writerow([author, count])


def generate_files_csv(files_changed):
    with open('files_report.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['File Path', 'Change Count'])
        for file, count in sorted(files_changed.items(), key=lambda x: x[1], reverse=True):
            writer.writerow([file, count])


if __name__ == "__main__":
    result = generate_report()
    print(result)