import re
from util import shell_util, file_util
from model.loc import LOC
from analyzer import xml_analyzer
from conf import config


CLOC_COMMAND = config.get_cloc_command()


def get_java_kotlin_sloc(path: str, commit_id=None):
    return get_java_kotlin_loc(path, commit_id).code_num


def get_java_kotlin_loc(path: str, commit_id=None):
    if commit_id is None:
        output = shell_util.run_command(CLOC_COMMAND + " --include-lang=Java,Kotlin --not-match-f='^[Mm]ock|[Mm]ock$|.*[Tt]est.*' '{}'".format(path))
    else:
        output = shell_util.run_command(CLOC_COMMAND + " --include-lang=Java,Kotlin --not-match-f='^[Mm]ock|[Mm]ock$|.*[Tt]est.*' '{}' {}".format(path, commit_id), cwd=path)
    pattern = '.*SUM.*'
    m = re.search(pattern, output)
    result = LOC()
    if m is not None:
        line = m.group(0)
        result = _convert_cloc_line_to_object(line)

    return result


def _convert_cloc_line_to_object(line) -> LOC:
    split_line = line.strip().split()
    files_num = int(split_line[1])
    blank_num = int(split_line[2])
    comment_num = int(split_line[3])
    code_num = int(split_line[4])
    return LOC(files_num, blank_num, comment_num, code_num)


def get_logging_loc_of_repo(path: str, repo_url: str, csv_path):
    return len(xml_analyzer.get_logging_calls_xml_of_repo(path, repo_url, csv_path))


def get_logging_loc_of_file(path: str, keyword_list):
    return len(xml_analyzer.get_logging_calls_xml_of_file(path, keyword_list))


def get_file_loc_diff(old_path: str, new_path: str):
    output = shell_util.run_command(CLOC_COMMAND + " --diff --diff-timeout 1000 '{}' '{}'".format(old_path, new_path))

    if file_util.is_java_file(old_path):
        pattern = '.*Java(\s.*){4}'
    else:
        pattern = '.*Kotlin(\s.*){4}'
    m = re.search(pattern, output)
    same = LOC()
    modified = LOC()
    added = LOC()
    removed = LOC()

    if m is not None:
        lines = m.group(0).split('\n')
        lines.pop(0)
        for line in lines:
            line_type = line.split()[0]
            loc_detail = _convert_cloc_line_to_object(line)
            if line_type == 'same':
                same = loc_detail
            elif line_type == 'modified':
                modified = loc_detail
            elif line_type == 'added':
                added = loc_detail
            elif line_type == 'removed':
                removed = loc_detail

    return {
        'same': same,
        'modified': modified,
        'added': added,
        'removed': removed
    }
