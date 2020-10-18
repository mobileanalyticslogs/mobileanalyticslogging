from postgresql import model_operator
from analyzer import repo_analyzer
from conf import config


def all_repo_analyzer(csv_path):
    model_operator.create_tables()
    model_operator.save_repos_to_db(csv_path)
    all_repos = model_operator.get_all_repos()
    for repo in all_repos:
        print(repo.url)
        repo_analyzer.detect_repo(repo, csv_path)


if __name__ == '__main__':
    # model_operator.create_tables()
    # model_operator.save_repos_to_db(config.REPO_INFO_CSV_PATH)
    all_repo_analyzer(config.REPO_INFO_CSV_PATH)
