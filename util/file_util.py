import csv
import os
import re
import uuid

import pandas as pd
from pathlib import Path
from util import shell_util


def get_project_name_list(csv_path):
    column_names = ['Keyword', 'Layout', 'LoggingLibrary', 'ProjectInfo', 'SearchResult']
    csv_data = pd.read_csv(csv_path, names=column_names)
    project_info_list = csv_data.ProjectInfo.tolist()
    return project_info_list[1:]


def export_info_to_csv(list_to_export, csv_path):
    with open(csv_path, "w") as f_output:
        csv_output = csv.writer(f_output)
        csv_output.writerow(['repo url', 'earliest committer', 'second earliest committer', 'latest committer',
                             'top three contributor', 'total commit'])
        csv_output.writerows(list_to_export)


def get_project_repo_url(csv_path: str):
    df = pd.read_csv(csv_path)
    repo_url_list = df['repo url'].to_list()
    return repo_url_list


def get_project_repo_id(csv_path: str, repo_url: str):
    df = pd.read_csv(csv_path)
    new_df = df[df["repo url"] == repo_url]
    repo_id = new_df['repo id']
    return repo_id


def get_keyword_list(csv_path: str, repo_url: str):
    df = pd.read_csv(csv_path)
    new_df = df[df["repo url"] == repo_url]
    keyword_list = new_df['keyword'].to_list()
    str_keyword = keyword_list[0]
    replaced_str_keyword = str_keyword.replace('\n', ' ').replace('\r', ' ')
    list_str_keyword = replaced_str_keyword.split(' ')
    list_str_keyword = list(filter(None, list_str_keyword))
    return list_str_keyword


def get_all_java_kotlin_files(repo_path: str) -> [Path]:
    repo_p = Path(repo_path)
    try:
        java_file_list = list(repo_p.glob('**/*.java'))
        kt_file_list = list(repo_p.glob('**/*.kt'))
        ktm_file_list = list(repo_p.glob('**/*.ktm'))
        kts_file_list = list(repo_p.glob('**/*.kts'))
        file_list = java_file_list + kt_file_list + ktm_file_list + kts_file_list
    except Exception:
        file_list = shell_util.run_command\
            ('find {} -name "*.java" -o -name "*.kt" -o -name "*.ktm" -o -name "*.kts"'.format(repo_path)).split()

    for file in file_list:
        if is_test_file(str(file)):
            file_list.remove(file)

    return file_list


def generate_random_file_name_with_extension(file_extension: str) -> str:
    return "{}.{}".format(generate_hex_uuid_4(), file_extension)


def generate_hex_uuid_4() -> str:
    """Generate UUID (version 4) in hexadecimal representation.
    :return: hexadecimal representation of version 4 UUID.
    """
    return str(uuid.uuid4().hex)


def is_test_file(file_path: str):
    result = False
    file_name = os.path.basename(file_path)
    pattern = '^[Mm]ock|[Mm]ock$|.*[Tt]est.*'
    match = re.search(pattern, file_name)
    # print(match)
    if match is not None:
        result = True

    return result


def is_java_or_kotlin_file(file_path: str):
    if file_path.endswith('.java') or file_path.endswith('.kt') or file_path.endswith('.ktm') \
            or file_path.endswith('.kts'):
        return True
    else:
        return False


def generate_file_from_blob(file_blob, file_extension):
    java_name = generate_random_file_name_with_extension(file_extension)
    java_p = Path(java_name)
    java_p.write_bytes(file_blob.data_stream.read())
    return str(java_p.resolve())


def delete_if_exists(file_path: str):
    path = Path(file_path)
    if path.exists():
        path.unlink()


def is_java_file(file_path: str):
    if file_path.endswith('.java'):
        return True
    else:
        return False
