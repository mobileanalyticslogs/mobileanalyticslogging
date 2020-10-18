import git
import re
from conf import config
from util import shell_util
from datetime import datetime

# stackoverflow
EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
insertion_pattern = re.compile('(\d+) insertion')
deletion_pattern = re.compile('(\d+) deletion')

def get_default_branch(path: str):
    output = shell_util.run_command("git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@' | tr -d ' '", cwd=path)
    return output.strip()


def checkout_default_branch(path: str):
    git_repo = get_project_repository(path)
    g = git_repo.git
    default_branch = get_default_branch(path)
    print(default_branch)
    g.checkout('-f', default_branch)


def get_project_repository(path: str):
    repository = git.Repo(path)
    assert not repository.bare
    return repository


def reset(git_repo):
    g = git_repo.git
    g.reset('--hard')


def clone_git_repos(repo_url_list: list):
    for item in repo_url_list:
        clone_url = item + ".git"
        print(clone_url)
        app_name = item.split('/')[-1]
        local_repo_path = config.APM_REPO_PATH + app_name
        shell_util.run_command("git clone {} '{}'".format(clone_url, local_repo_path))


def get_diff_between_commits(parent_commit, head_commit):
    return parent_commit.diff(head_commit, create_patch=False)


def get_diff_of_initial_commit(git_repo, initial_commit):
    # See https://stackoverflow.com/questions/33916648/get-the-diff-details-of-first-commit-in-gitpython
    return git_repo.tree(EMPTY_TREE_SHA).diff(initial_commit, create_patch=False)


def get_non_merge_commits(path: str):
    git_repo = get_project_repository(path)
    g = git_repo.git
    result = g.log('--no-merges', '--oneline', '--pretty=%H').split('\n')
    return result


def get_all_commits(path: str):
    git_repo = get_project_repository(path)
    g = git_repo.git
    result = g.log('--oneline', '--pretty=%H').split('\n')
    return result


def refresh_git_repo(path: str):
    git_repo = get_project_repository(path)
    reset(git_repo)
    checkout_default_branch(path)


def refresh_and_pull_git_repo(path: str):
    git_repo = get_project_repository(path)
    reset(git_repo)
    checkout_default_branch(path)
    git_repo.git.pull()


def get_files_num(path: str):
    output = shell_util.run_command("git ls-files | wc -l | tr -d ' '", cwd=path)
    return int(output)


def get_commits_num(path: str):
    output = shell_util.run_command("git log --oneline $commit | wc -l | tr -d ' '", cwd=path)
    return int(output)


def get_repo_age_str(path: str):
    output = shell_util.run_command("git log --reverse --pretty=oneline --format='%ar' | head -n 1 | LC_ALL=C sed 's/ago//' | tr -d ' '", cwd=path)
    return output


def get_last_commit_date(path: str):
    output = shell_util.run_command("git log --pretty='format: %ai' | head -n 1", cwd=path)
    datetime_str = output.strip()
    return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S %z')


def get_first_commit_date(path: str):
    output = shell_util.run_command("git log --reverse --pretty='format: %ai' | head -n 1", cwd=path)
    datetime_str = output.strip()
    return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S %z')


def get_authors_num(path: str):
    output = shell_util.run_command("git log --format='%aN' | sort -u | wc -l | tr -d ' '", cwd=path)
    return int(output)


def get_code_churn_between_commits(path: str, old_commit, new_commit):
    output = shell_util.run_command("git diff --shortstat {} {} -- '*.java' | head -n 1".format(old_commit, new_commit), cwd=path)
    added_count = 0
    deleted_count = 0
    added_match = insertion_pattern.search(output)
    if added_match:
        added_count = int(added_match.group(1))
    deleted_match = deletion_pattern.search(output)
    if deleted_match:
        deleted_count = int(deleted_match.group(1))

    return added_count + deleted_count
