from lxml import etree
import re
import model.repository
import model.base_model
import model.commit
import model.log
from conf import config

from util import file_util, git_util
from analyzer import xml_analyzer

def create_tables():
    model.base_model.db.connect()
    model.base_model.db.create_tables([model.repository.Repository, model.commit.Commit, model.log.Log], safe=True)


def get_all_repos() -> [model.repository.Repository]:
    return model.repository.Repository.select()


def get_logs_of_repo(repo: model.repository.Repository) -> [model.log.Log]:
    return model.log.Log.select().join(model.commit.Commit) \
        .where((model.commit.Commit.repository == repo.url) & (model.commit.Commit.is_merge_commit is False)) \
        .order_by(model.commit.Commit.committed_date.desc())


def save_repos_to_db(csv_path: str):
    repo_url_list = file_util.get_project_repo_url(csv_path)
    git_util.clone_git_repos(repo_url_list)
    # repo_url_list = ['https://github.com/StepicOrg/stepik-android', 'https://github.com/niranjan94/show-java']

    for repo_url in repo_url_list:
        repo_name = repo_url.split('/')[-1]

        app_url = repo_url
        app_id = file_util.get_project_repo_id(csv_path, repo_url)
        app_name = repo_name

        repo = model.repository.Repository.get_or_none(model.repository.Repository.url == repo_url)

        if repo is None:
            model.repository.Repository.create(url=app_url, app_id=app_id, name=app_name)
        else:
            repo.app_id = app_id
            repo.name = app_name
            repo.save()


def save_logs_of_method_xml_str_if_needed(head_commit_db, file_path, method_xml, change_type, logging_calls,
                                          is_java_file):
    if is_java_file is not None:
        if is_java_file:
            method_name = xml_analyzer.get_method_full_signature(method_xml)
        else:
            method_name = 'kotlin_cannot_identify'
    else:
        method_name = 'NILL'

    replaced_file_path = file_path.replace(config.APM_REPO_PATH, '')
    for call_xml in logging_calls:
        call_text = xml_analyzer.transform_xml_str_to_code(etree.tostring(call_xml).decode('utf-8'))
        call_text = call_text.replace('\\n', '').replace('\\r', '').replace('\\t', '')
        format_call_text = re.sub(' +', ' ', call_text)
        model.log.Log.create(commit=head_commit_db, file_path=replaced_file_path, embed_method=method_name,
                             change_type=change_type, content=format_call_text)

    # return len(logging_calls)
