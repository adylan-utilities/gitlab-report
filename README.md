# gitlab-report
This repo is to create the gitlab reports. e.g. all_author_report, all_commit_report, all_files_report

To use this script:

Make sure you have the required libraries installed:
```shell
pip install requests python-dateutil
```
Set the environment variables:

Ensure your GitLab instance URL if self-hosted, is set as an environment variable:
```shell
export GITLAB_URL=your_gitlab_instane_url
```

Ensure your GitLab token is set as an environment variable:
```shell
export GITLAB_TOKEN=your_gitlab_token_here
```

Run the script with your desired parameters:
```shell
 python all-projects-report-csv-format-with-date-range.py 2024-09-20 2024-09-28 --reports authors commits files
```