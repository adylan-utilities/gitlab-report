import requests
import csv
from datetime import datetime, timedelta
from collections import defaultdict

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


def get_commits(project_id, branch, since_date):
    commits = []
    page = 1
    while True:
        response = requests.get(
            f"{GITLAB_URL}/api/v4/projects/{project_id}/repository/commits",
            params={"ref_name": branch, "since": since_date, "page": page, "per_page": 100},
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


def generate_report(days=7):
    since_date = (datetime.now() - timedelta(days=days)).isoformat()
    projects = get_all_projects()

    all_commits = []
    all_authors = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    all_files = defaultdict(int)

    for project in projects:
        project_id = project['id']
        project_name = project['name']
        branches = get_project_branches(project_id)

        for branch in branches:
            branch_name = branch['name']
            commits = get_commits(project_id, branch_name, since_date)

            for commit in commits:
                commit['project_name'] = project_name
                commit['branch_name'] = branch_name
                all_commits.append(commit)
                all_authors[commit['author_name']][project_name][branch_name] += 1
                details = get_commit_details(project_id, commit['id'])
                for file in details:
                    all_files[f"{project_name}: {branch_name}: {file['new_path']}"] += 1

    generate_commits_csv(all_commits)
    generate_authors_csv(all_authors)
    generate_files_csv(all_files)

    return f"Report generated for {len(projects)} projects"


def generate_commits_csv(commits):
    with open('all_commits_report.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Project', 'Branch', 'Commit ID', 'Author', 'Date', 'Message'])
        for commit in commits:
            writer.writerow([
                commit['project_name'],
                commit['branch_name'],
                commit['short_id'],
                commit['author_name'],
                commit['created_at'],
                commit['title']
            ])


def generate_authors_csv(authors):
    with open('all_authors_report.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Author', 'Project', 'Branch', 'Commit Count'])
        for author, projects in authors.items():
            for project, branches in projects.items():
                for branch, count in branches.items():
                    writer.writerow([author, project, branch, count])


def generate_files_csv(files_changed):
    with open('all_files_report.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Project: Branch: File Path', 'Change Count'])
        for file, count in sorted(files_changed.items(), key=lambda x: x[1], reverse=True):
            writer.writerow([file, count])


if __name__ == "__main__":
    result = generate_report()
    print(result)