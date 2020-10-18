from model.repository import Repository
from model.commit import Commit
from conf import config
from util import git_util, loc_util, file_util
from analyzer import commit_analyzer


def calculate_initial_metrics(repo: Repository, csv_path):
    repo_path = config.APM_REPO_PATH + repo.name

    local_last_commit_date = git_util.get_last_commit_date(repo_path)
    if repo.last_commit_date is None or local_last_commit_date > repo.last_commit_date:
        repo.files_num = len(file_util.get_all_java_kotlin_files(repo_path))
        repo.commits_num = git_util.get_commits_num(repo_path)
        repo.last_commit_date = local_last_commit_date
        repo.first_commit_date = git_util.get_first_commit_date(repo_path)
        repo.authors_num = git_util.get_authors_num(repo_path)
        repo.sloc = loc_util.get_java_kotlin_sloc(repo_path)
        repo.logging_loc = loc_util.get_logging_loc_of_repo(repo_path, repo.url, csv_path)
        repo.save()


def _is_commit_analyzed(commit: Commit):
    return commit.code_churn is not None


def detect_repo(repo: Repository, csv_path):
    print('processing {}'.format(repo.name))
    calculate_initial_metrics(repo, csv_path)
    repo_path = config.APM_REPO_PATH + repo.name

    commit_list = git_util.get_all_commits(repo_path)
    git_repo = git_util.get_project_repository(repo_path)

    for i in range(0, len(commit_list)):
        head_commit_sha = commit_list[i]
        head_commit = git_repo.commit(head_commit_sha)

        is_merge_commit = False
        print('current commit: {}'.format(head_commit_sha))
        if head_commit.parents:
            if len(head_commit.parents) > 1:
                is_merge_commit = True
            # Attempt to get the row matching the given filters. If no matching row is found, create a new row.
            # return tuple of Model instance and boolean indicating if a new object was created.
            head_commit_db = Commit.get_or_create(repo=repo, commit_id=head_commit_sha)[0]
            head_commit_db.is_merge_commit = is_merge_commit

            if i == 0:
                head_commit_db.sloc = repo.sloc
                head_commit_db.logging_loc = repo.sloc
            for parent_commit in head_commit.parents:
                parent_commit_sha = parent_commit.hexsha
                diff = git_util.get_diff_between_commits(parent_commit, head_commit)
                head_commit_db.parent_commit_id = parent_commit_sha
                parent_commit_db = Commit.get_or_create(repo=repo, commit_id=parent_commit_sha)[0]
                if _is_commit_analyzed(head_commit_db) and _is_commit_analyzed(parent_commit_db):
                    continue

                sloc = head_commit_db.sloc
                logging_loc = head_commit_db.logging_loc
                sloc_delta, logging_loc_delta = commit_analyzer.diff_analyzer(git_repo, diff, head_commit_db, repo.url)
                sloc -= sloc_delta
                logging_loc -= logging_loc_delta
                parent_commit_db.sloc = sloc
                # parent_commit_db.logging_loc = logging_loc
                parent_commit_db.save()
        else:
            # Initial Commit
            diff = git_util.get_diff_of_initial_commit(git_repo, head_commit)
            head_commit_db = Commit.get_or_create(repo=repo, commit_id=head_commit_sha)[0]
            if not _is_commit_analyzed(head_commit_db):
                commit_analyzer.diff_analyzer(git_repo, diff, head_commit_db, repo.url)
