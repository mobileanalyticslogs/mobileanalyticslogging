import random
from collections import Counter

from graphql.contributor_info_query import ContributorInfoQuery
from conf import config
from util.file_util import get_project_name_list, export_info_to_csv


def get_repo_contributor_info(csv_path) -> dict:
    project_name_list = get_project_name_list(csv_path)
    # remove duplicate project
    project_name_list.remove("ItsCalebJones/SpaceLaunchNow-Android")
    project_name_list.remove("spongebobrf/BookdashAndroidApp")
    project_name_list.remove("RocketChat/Rocket.Chat.Android.Lily")
    repo_contributor_info_dict = {}
    for repo_name in project_name_list:
        print(repo_name)
        github_url = 'https://github.com/{repo_name}'.format(repo_name=repo_name)
        variables = {
            "owner": repo_name.split('/')[0],
            "name": repo_name.split('/')[1]
        }
        temp_contributor_info_list = \
            ContributorInfoQuery(config.GITHUB_TOKEN, config.REPO_INFO_QUERY, variables).iterator()
        repo_contributor_info_dict[github_url] = temp_contributor_info_list

    return repo_contributor_info_dict


def analyse_repo_contributor_dict(csv_path):
    repo_contributor_info_dict = get_repo_contributor_info(csv_path)
    list_to_export = []
    for key in repo_contributor_info_dict.keys():
        repo_git_url = key
        repo_commit_num = len(repo_contributor_info_dict[key])
        earliest_commit_email = repo_contributor_info_dict[key][repo_commit_num - 1]["node"]["author"]["email"]
        earliest_commit_name = repo_contributor_info_dict[key][repo_commit_num - 1]["node"]["author"]["name"]
        earliest_committer = earliest_commit_email + ":" + earliest_commit_name
        second_earliest_commit_email = repo_contributor_info_dict[key][repo_commit_num - 2]["node"]["author"]["email"]
        second_earliest_commit_name = repo_contributor_info_dict[key][repo_commit_num - 2]["node"]["author"]["name"]
        second_earliest_committer = second_earliest_commit_email + ":" + second_earliest_commit_name
        latest_commit_email = repo_contributor_info_dict[key][0]["node"]["author"]["email"]
        latest_commit_name = repo_contributor_info_dict[key][0]["node"]["author"]["name"]
        latest_committer = latest_commit_email + ":" + latest_commit_name
        top_contributor_list_str = get_top_three_contributors(repo_contributor_info_dict[key])
        list_to_export.append([repo_git_url, earliest_committer, second_earliest_committer, latest_committer,
                               top_contributor_list_str, repo_commit_num])

    return list_to_export


def get_top_three_contributors(repo_contributor_info_list):
    email_name_list = []
    for json_item in repo_contributor_info_list:
        email = json_item["node"]["author"]["email"]
        name = json_item["node"]["author"]["name"]
        email_name_list.append((email, name))

    # get element:frequency hash map
    element_frequency_map = Counter(email_name_list)
    # get unique element list
    unique_element = list(element_frequency_map.keys())
    unique_element_length = len(unique_element)
    if unique_element_length >= 3:
        unique_element = quick_select(0, unique_element_length - 1, unique_element_length - 3, unique_element,
                                      element_frequency_map)
        active_contributor = unique_element[unique_element_length - 3:]
    else:
        active_contributor = unique_element

    active_contributor_dict = {element: element_frequency_map[element] for element in active_contributor}
    sorted_active_contributor_list = {k: v for k, v in sorted(active_contributor_dict.items(),
                                                              key=lambda item: item[1], reverse=True)}
    result_string = ""
    for tuple_item in sorted_active_contributor_list.keys():
        email = tuple_item[0]
        name = tuple_item[1]
        email_name_string = email + ":" + name
        result_string = result_string + email_name_string + " "

    return result_string


def quick_select(left, right, k_smallest, unique_element, element_frequency_map):
    if left == right:
        return unique_element

    pivot_index = random.randint(left, right)
    pivot_index = hoare_partition(left, right, pivot_index, element_frequency_map, unique_element)
    if k_smallest == pivot_index:
        return unique_element
    elif pivot_index < k_smallest:
        return quick_select(pivot_index + 1, right, k_smallest, unique_element, element_frequency_map)
    else:
        return quick_select(left, pivot_index - 1, k_smallest, unique_element, element_frequency_map)


def hoare_partition(left, right, pivot_index, element_frequency_map, unique_element):
    pivot_frequency = element_frequency_map[unique_element[pivot_index]]
    unique_element[pivot_index], unique_element[right] = unique_element[right], unique_element[pivot_index]
    store_index = left
    for index in range(left, right):
        if element_frequency_map[unique_element[index]] < pivot_frequency:
            unique_element[store_index], unique_element[index] = unique_element[index], unique_element[store_index]
            store_index += 1

    unique_element[right], unique_element[store_index] = unique_element[store_index], unique_element[right]
    return store_index


if __name__ == '__main__':
    contributor_info_list = analyse_repo_contributor_dict('../data/analytics_repo_list.csv')
    export_info_to_csv(contributor_info_list, '../data/repo_owner_email_info_v2.csv')
