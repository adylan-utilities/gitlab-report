import requests
import datetime
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
    since_date = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    project = get_project_info()

    if not project:
        return "Failed to fetch project information."

    report = f"# GitLab Commit Report for {project['name']} (Last {days} days)\n\n"

    commits = get_commits(since_date)
    total_commits = len(commits)
    authors = defaultdict(int)
    files_changed = defaultdict(int)

    report += f"## Project: {project['name']}\n"
    report += f"Description: {project['description']}\n"
    report += f"Total commits: {total_commits}\n\n"

    for commit in commits:
        authors[commit['author_name']] += 1
        details = get_commit_details(commit['id'])
        for file in details:
            files_changed[file['new_path']] += 1

    report += "## Recent Commits\n\n"
    for commit in commits[:10]:  # Show the 10 most recent commits
        report += f"- {commit['short_id']} - {commit['author_name']} - {commit['created_at']}: {commit['title']}\n"
    report += "\n"

    report += "## Statistics\n\n"

    report += "### Top Contributors\n\n"
    for author, count in sorted(authors.items(), key=lambda x: x[1], reverse=True):
        report += f"- {author}: {count} commits\n"
    report += "\n"

    report += "### Most Changed Files\n\n"
    for file, count in sorted(files_changed.items(), key=lambda x: x[1], reverse=True)[:10]:
        report += f"- {file}: changed {count} times\n"

    return report


if __name__ == "__main__":
    report = generate_report()
    print(report)

    # Optionally, save the report to a file
    with open("gitlab_commit_report.md", "w") as f:
        f.write(report)