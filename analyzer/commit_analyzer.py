import Levenshtein
from lxml import etree
from postgresql import model_operator
from model.commit import Commit
from model.log import LogChangeType, Log
from util import file_util, loc_util
from conf import config
from analyzer import xml_analyzer


def diff_analyzer(git_repo, commit_diff, head_commit_db: Commit, repo_url):
    head_commit_sha = head_commit_db.commit_id
    head_commit_git = git_repo.commit(head_commit_sha)
    head_commit_db.committer_name = head_commit_git.committer.name
    head_commit_db.committer_email = head_commit_git.committer.email
    head_commit_db.committed_date = head_commit_git.committed_datetime
    head_commit_db.author_name = head_commit_git.author.name
    head_commit_db.author_email = head_commit_git.author.email
    head_commit_db.authored_date = head_commit_git.authored_datetime
    head_commit_db.message = head_commit_git.message

    repo_added_sloc = 0
    repo_deleted_sloc = 0
    repo_updated_sloc = 0

    repo_added_logging_loc = 0
    repo_deleted_logging_loc = 0
    repo_updated_logging_loc = 0

    for file_diff in commit_diff:

        if file_diff.change_type == 'A':
            file_sloc, file_logging_loc = handle_added_file(file_diff, head_commit_db, repo_url)
            repo_added_sloc += file_sloc
            repo_added_logging_loc += file_logging_loc
        elif file_diff.change_type == 'D':
            file_sloc, file_logging_loc = handle_deleted_file(file_diff, head_commit_db, repo_url)
            repo_deleted_sloc += file_sloc
            repo_deleted_logging_loc += file_logging_loc
        elif file_diff.change_type == 'M' or \
                (file_diff.change_type.startswith('R') and file_diff.a_blob != file_diff.b_blob):
            file_added_sloc, file_deleted_sloc, file_updated_sloc, file_added_logging_loc, file_deleted_logging_loc, file_updated_logging_loc = \
                handle_updated_file(file_diff, head_commit_db, repo_url)

            repo_added_sloc += file_added_sloc
            repo_deleted_sloc += file_deleted_sloc
            repo_updated_sloc += file_updated_sloc
            repo_added_logging_loc += file_added_logging_loc
            repo_deleted_logging_loc += file_deleted_logging_loc
            repo_updated_logging_loc += file_updated_logging_loc

    code_churn = repo_added_sloc + repo_deleted_sloc + (repo_updated_sloc * 2)
    sloc_delta = repo_added_sloc - repo_deleted_sloc
    logging_code_churn = repo_added_logging_loc + repo_deleted_logging_loc + (repo_updated_logging_loc * 2)
    logging_loc_delta = repo_added_logging_loc - repo_deleted_logging_loc

    head_commit_db.code_churn = code_churn
    # head_commit_db.logging_code_churn = logging_code_churn
    head_commit_db.save()

    return sloc_delta, logging_loc_delta


def handle_added_file(file_diff, head_commit_db: Commit, repo_url):
    return handle_added_or_deleted_file(file_diff.b_path, file_diff.b_blob,
                                        LogChangeType.LOG_ADDED, head_commit_db, repo_url)


def handle_deleted_file(file_diff, head_commit_db: Commit, repo_url):
    return handle_added_or_deleted_file(file_diff.a_path, file_diff.a_blob,
                                        LogChangeType.LOG_DELETED, head_commit_db, repo_url)


def handle_added_or_deleted_file(file_path, file_blob, change_type, head_commit_db: Commit, repo_url):
    file_sloc = 0
    file_logging_loc = 0

    keyword_list = file_util.get_keyword_list(config.REPO_INFO_CSV_PATH, repo_url)

    if file_util.is_java_or_kotlin_file(file_path):
        file_extension = file_path.split('.')[-1]
        src_file = file_util.generate_file_from_blob(file_blob, file_extension)
        file_sloc = loc_util.get_java_kotlin_sloc(src_file)
        file_logging_loc = loc_util.get_logging_loc_of_file(src_file, keyword_list)
        file_util.delete_if_exists(src_file)

        if not head_commit_db.is_merge_commit:
            is_java_file = file_util.is_java_file(file_path)
            methods = xml_analyzer.get_methods_from_blob(file_blob, is_java_file)
            for method in methods:
                method_str = b'<root>' + etree.tostring(method) + b'</root>'
                parser = etree.XMLParser(huge_tree=True, encoding='utf-8', ns_clean=True, recover=True)
                method_xml = etree.fromstring(method_str, parser)
                logging_calls = xml_analyzer.get_logging_calls_xml_of_method(method_xml, keyword_list, is_java_file)

                model_operator.save_logs_of_method_xml_str_if_needed(head_commit_db, file_path, method_xml,
                                                                     change_type, logging_calls, is_java_file)

    return file_sloc, file_logging_loc


def handle_updated_file(file_diff, head_commit_db: Commit, repo_url):
    file_added_sloc = 0
    file_deleted_sloc = 0
    file_updated_sloc = 0
    file_added_logging_loc = 0
    file_deleted_logging_loc = 0
    file_updated_logging_loc = 0

    if file_util.is_java_or_kotlin_file(file_diff.a_path) and file_util.is_java_or_kotlin_file(file_diff.b_path):
        file_extension = file_diff.a_path.split('.')[-1]
        src_a_file = file_util.generate_file_from_blob(file_diff.a_blob, file_extension)
        src_b_file = file_util.generate_file_from_blob(file_diff.b_blob, file_extension)
        loc_diff = loc_util.get_file_loc_diff(src_a_file, src_b_file)
        file_util.delete_if_exists(src_a_file)
        file_util.delete_if_exists(src_b_file)

        file_added_sloc = loc_diff['added'].code_num
        file_deleted_sloc = loc_diff['removed'].code_num
        file_updated_sloc = loc_diff['modified'].code_num

        is_java_file = file_util.is_java_file(file_diff.a_path)
        keyword_list = file_util.get_keyword_list(config.REPO_INFO_CSV_PATH, repo_url)

        logging_calls_in_parent = xml_analyzer.get_logging_calls_from_blob(file_diff.a_blob, is_java_file, keyword_list)
        logging_calls_in_head = xml_analyzer.get_logging_calls_from_blob(file_diff.b_blob, is_java_file, keyword_list)

        file_added_logging_loc, file_deleted_logging_loc, file_updated_logging_loc = \
            compare_logging_calls(head_commit_db, file_diff, logging_calls_in_parent,
                                  logging_calls_in_head)

    return file_added_sloc, file_deleted_sloc, file_updated_sloc, file_added_logging_loc, file_deleted_logging_loc, file_updated_logging_loc


def compare_logging_calls(head_commit_db, file_diff, logging_calls_in_parent, logging_calls_in_head):
    file_mapping_list = []
    file_added_logging_loc = 0
    file_deleted_logging_loc = 0
    file_updated_logging_loc = 0

    # Add index to make each call unique.
    logging_calls_str_parent = \
        [str(index) + '#' + etree.tostring(call).decode('utf-8') for index, call in
         enumerate(logging_calls_in_parent)]
    logging_calls_str_head = \
        [str(index) + '#' + etree.tostring(call).decode('utf-8') for index, call in
         enumerate(logging_calls_in_head)]

    for call_str_in_parent in logging_calls_str_parent:
        for call_str_in_head in logging_calls_str_head:
            distance_ratio = Levenshtein.ratio(xml_analyzer.transform_xml_str_to_code(call_str_in_parent),
                                               xml_analyzer.transform_xml_str_to_code(call_str_in_head))
            if distance_ratio > config.LEVENSHTEIN_RATIO_THRESHOLD:
                is_parent_in_mapping = False
                # Check mapping list
                for mapping in file_mapping_list:
                    call_mapping_parent = mapping[0]
                    mapping_ratio = mapping[2]
                    if call_str_in_parent == call_mapping_parent:
                        is_parent_in_mapping = True
                        if distance_ratio > mapping_ratio:
                            mapping[1] = call_str_in_head
                            mapping[2] = Levenshtein.ratio(_get_code_text_from_compare(call_str_in_parent),
                                                           _get_code_text_from_compare(call_str_in_head))
                if not is_parent_in_mapping:
                    is_head_in_mapping = False
                    for mapping in file_mapping_list:
                        call_mapping_head = mapping[1]
                        mapping_ratio = mapping[2]
                        if call_str_in_head == call_mapping_head:
                            is_head_in_mapping = True
                            if distance_ratio > mapping_ratio:
                                mapping[0] = call_str_in_parent
                                mapping[2] = Levenshtein.ratio(_get_code_text_from_compare(call_str_in_parent),
                                                               _get_code_text_from_compare(call_str_in_head))
                    if not is_head_in_mapping:
                        file_mapping_list.append([call_str_in_parent, call_str_in_head, distance_ratio])

    file_calls_mapping_in_parent = [mapping[0] for mapping in file_mapping_list]
    file_calls_mapping_in_head = [mapping[1] for mapping in file_mapping_list]

    deleted_logging_calls_str = list(set(logging_calls_str_parent) - set(file_calls_mapping_in_parent))
    added_logging_calls_str = list(set(logging_calls_str_head) - set(file_calls_mapping_in_head))

    file_deleted_logging_loc += len(deleted_logging_calls_str)
    file_added_logging_loc += len(added_logging_calls_str)

    if not head_commit_db.is_merge_commit:
        for call_str in deleted_logging_calls_str:
            call_xml = etree.fromstring(_get_code_xml_str_from_compare(call_str))
            model_operator.save_logs_of_method_xml_str_if_needed(head_commit_db, file_diff.a_path, None,
                                                                 LogChangeType.LOG_DELETED, call_xml, None)

        for call_str in added_logging_calls_str:
            call_xml = etree.fromstring(_get_code_xml_str_from_compare(call_str))
            model_operator.save_logs_of_method_xml_str_if_needed(head_commit_db, file_diff.a_path, None,
                                                                 LogChangeType.LOG_ADDED, call_xml, None)

    for mapping in file_mapping_list:
        change_from = _get_code_text_from_compare(mapping[0])
        change_to = _get_code_text_from_compare(mapping[1])
        if change_from != change_to:
            # True Update
            file_updated_logging_loc += 1
            if not head_commit_db.is_merge_commit:
                log = Log.create(commit=head_commit_db, file_path=file_diff.b_path, embed_method='NILL',
                                 change_type=LogChangeType.LOG_UPDATED, content=change_to,
                                 content_update_from=change_from)
                log.save()

    return file_added_logging_loc, file_deleted_logging_loc, file_updated_logging_loc


def _get_code_xml_str_from_compare(xml_str):
    return xml_str.split('#', 1)[1]


def _get_code_text_from_compare(xml_str):
    return xml_analyzer.transform_xml_str_to_code(_get_code_xml_str_from_compare(xml_str))
