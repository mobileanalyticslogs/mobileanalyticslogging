from matplotlib.ticker import MaxNLocator

import model.commit
import model.repository
import pandas as pd
import re
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np
import scipy.stats


def get_churn_rate_of_commit(commit: model.commit.Commit):
    if commit.code_churn is not None and commit.sloc > 0:
        return commit.code_churn / commit.sloc
    else:
        return 0


def get_logging_churn_rate_of_commit(commit: model.commit.Commit):
    if commit.logging_code_churn is not None and commit.logging_loc > 0:
        return commit.logging_code_churn / commit.logging_loc
    else:
        return 0


def get_average_churn_rate_of_repo(repo: model.repository.Repository):
    if repo.is_repo_valid():
        commits = repo.get_non_merge_commits()
        return sum(get_churn_rate_of_commit(commit) for commit in commits) / len(commits)
    else:
        return None


def get_average_logging_churn_rate_or_repo(repo: model.repository.Repository):
    if repo.is_repo_valid():
        commits = repo.get_non_merge_commits()
        return sum(get_logging_churn_rate_of_commit(commit) for commit in commits) / len(commits)
    else:
        return None


def get_updated_log(csv_path: str, write_to: str):
    df = pd.read_csv(csv_path)
    new_df = df[df["change_type"] == "LOG_UPDATED"]
    new_df.to_csv(write_to)


def remove_str_ctrl_char(csv_path: str):
    regex = re.compile(r'[\n\r\t]')
    df = pd.read_csv(csv_path)
    id_list = df["id"].to_list()
    commit_fk_list = df["commit_fk"].to_list()
    file_path_list = df["file_path"].to_list()
    original_log_list = df["content_update_from"].to_list()
    updated_log_list = df["content"].to_list()

    file_appearance_map = Counter(file_path_list)
    print(len(file_appearance_map))
    for item in file_appearance_map.keys():
        print(item)
        print(file_appearance_map[item])


def adjacent_values(vals, q1, q3):
    upper_adjacent_value = q3 + (q3 - q1) * 1.5
    upper_adjacent_value = np.clip(upper_adjacent_value, q3, vals[-1])

    lower_adjacent_value = q1 - (q3 - q1) * 1.5
    lower_adjacent_value = np.clip(lower_adjacent_value, vals[0], q1)
    return lower_adjacent_value, upper_adjacent_value


def set_axis_style(ax, labels):
    ax.get_xaxis().set_tick_params(direction='out')
    ax.xaxis.set_ticks_position('bottom')
    ax.set_xticks(np.arange(1, len(labels) + 1))
    ax.set_xticklabels(labels)
    ax.set_xlim(0.25, len(labels) + 0.75)


def draw_violin_plot(csv_path: str):
    df = pd.read_csv(csv_path)
    density_list = df["density"].tolist()

    fig, ax = plt.subplots()
    ax.set_ylabel('Mobile analytics log density')
    bp = ax.violinplot(density_list,showmeans=False, showmedians=False,showextrema=False)
    for pc in bp['bodies']:
        pc.set_facecolor('#D43F3A')
        pc.set_edgecolor('black')
        pc.set_alpha(1)

    quartile1, medians, quartile3 = np.percentile(density_list, [25, 50, 75], axis=0)
    whiskers = np.array([
        adjacent_values(density_list, quartile1, quartile3)
        ])
    whiskers_min, whiskers_max = whiskers[:, 0], whiskers[:, 1]

    inds = np.arange(1, 1 + 1)
    ax.scatter(inds, medians, marker='o', color='white', s=30, zorder=3)
    ax.vlines(inds, quartile1, quartile3, color='k', linestyle='-', lw=5)
    ax.vlines(inds, whiskers_min, whiskers_max, color='k', linestyle='-', lw=1)

    labels = ['']
    set_axis_style(ax, labels)

    # fig.set_tight_layout(False)
    # plt.savefig('fig.png', bbox_inches='tight')
    plt.subplots_adjust(bottom=0.15, wspace=0.05)
    plt.show()

    # sns.set(style="whitegrid")
    # # sns_df = sns.load_dataset(df)
    # sns.violinplot(y="density", data=df)
    # plt.show()


def calculate_average_churn_rate(churn_rate_csv: str, repo_to_analyze: str, merge_commit_csv: str):
    repo_df = pd.read_csv(repo_to_analyze)
    repo_url_list = repo_df["repo_url"].to_list()
    # repo_url_list = repo_url_list[-2]
    # print(repo_url_list)
    # logging_loc_list = repo_df["logging_loc"].to_list()
    # repo_url_list = ["https://github.com/StepicOrg/stepik-android", "https://github.com/niranjan94/show-java"]
    # avg_churn_rate_list =
    url_logging_loc_dict = dict(zip(repo_df.repo_url, repo_df.logging_loc))

    df = pd.read_csv(churn_rate_csv)
    merge_commit_df = pd.read_csv(merge_commit_csv)
    for each_url in repo_url_list:
        repo_per_url_df = repo_df[repo_df["repo_url"] == each_url]
        # print(repo_per_url_df["repo url"])
        final_logging_loc = url_logging_loc_dict[each_url]
        # print("final")
        # print(final_logging_loc)
        # print(type(final_logging_loc))
        current_commit_logging_loc = final_logging_loc

        repo_commit_num = repo_per_url_df["commit_num"]
        per_url_merge_commit_df = merge_commit_df[merge_commit_df["repo_fk"] == each_url]
        unique_per_url_merge_commit_df = per_url_merge_commit_df.drop_duplicates("commit_id")
        merge_commit_num = len(unique_per_url_merge_commit_df.index)
        repo_commit_num = repo_commit_num - merge_commit_num
        # print(repo_commit_num)

        per_url_df = df[df["repo_fk"] == each_url]
        unique_id_per_url_df = per_url_df.drop_duplicates("id")
        id_list = unique_id_per_url_df["id"].to_list()
        id_list.sort()
        repo_churn_rate_list = []
        for each_commit_id in id_list:
            per_commit_per_url_df = per_url_df[per_url_df["id"] == each_commit_id]
            tmp_add_df = per_commit_per_url_df[per_commit_per_url_df["change_type"] == "LOG_ADDED"]
            nill_added_log_num = len(tmp_add_df[tmp_add_df["embed_method"] == "NILL"])/2
            other_added_log_num = len(tmp_add_df[tmp_add_df["embed_method"] != "NILL"])

            tmp_delete_df = per_commit_per_url_df[per_commit_per_url_df["change_type"] == "LOG_DELETED"]
            nill_deleted_log_num = len(tmp_delete_df[tmp_delete_df["embed_method"] == "NILL"]) / 2
            other_deleted_log_num = len(tmp_delete_df[tmp_delete_df["embed_method"] != "NILL"])


            per_commit_added_log_num = nill_added_log_num + other_added_log_num
            per_commit_deleted_log_num = nill_deleted_log_num + other_deleted_log_num
            per_commit_updated_log_num = len(per_commit_per_url_df[per_commit_per_url_df["change_type"] == "LOG_UPDATED"])

            current_commit_log_churn = per_commit_added_log_num + per_commit_deleted_log_num + per_commit_updated_log_num
            # print(current_commit_logging_loc)
            current_commit_logging_loc = current_commit_logging_loc - per_commit_added_log_num + per_commit_deleted_log_num
            # print(current_commit_logging_loc)
            if current_commit_logging_loc > 0:
                current_commit_log_churn_rate = current_commit_log_churn/current_commit_logging_loc
            else:
                current_commit_log_churn_rate = 0

            repo_churn_rate_list.append(current_commit_log_churn_rate)

        print(each_url)
        print(sum(repo_churn_rate_list))
        print(sum(repo_churn_rate_list)/repo_commit_num)




def churn_rate_analysis(added_deleted_csv: str, updated_csv: str, repo_to_analyze: str, code_churn_csv: str):
    repo_url_df = pd.read_csv(repo_to_analyze)
    repo_url_list = repo_url_df["repo url"].to_list()
    added_deleted_df = pd.read_csv(added_deleted_csv)
    updated_df = pd.read_csv(updated_csv)

    code_churn_df = pd.read_csv(code_churn_csv)
    for url in repo_url_list:
        print(url)
        added_log_df = added_deleted_df[added_deleted_df["change_type"] == "LOG_ADDED"]
        repo_added_log_df = added_log_df[added_log_df["repo_fk"] == url]
        repo_added_log_num = len(repo_added_log_df.index)

        # /2
        # repo_code_churn_added_df = repo_added_log_df.drop_duplicates("commit_id")
        # repo_code_churn_added = repo_code_churn_added_df["code_churn"].sum()

        deleted_log_df = added_deleted_df[added_deleted_df["change_type"] == "LOG_DELETED"]
        repo_deleted_log_df = deleted_log_df[deleted_log_df["repo_fk"] == url]
        repo_deleted_log_num = len(repo_deleted_log_df.index)

        # /2
        # repo_code_churn_deleted_df = repo_deleted_log_df.drop_duplicates("commit_id")
        # repo_code_churn_deleted = repo_code_churn_deleted_df["code_churn"].sum()

        repo_updated_log_df = updated_df[updated_df["repo_fk"] == url]
        # print(repo_updated_log_df["repo_fk"])

        repo_updated_log_num = len(repo_updated_log_df.index)

        # print(repo_code_churn_added)
        # print(repo_code_churn_deleted)
        code_churn_df_no_merge = code_churn_df[code_churn_df["is_merge_commit"] == 'f']
        repo_code_churn_df_no_merge = code_churn_df_no_merge[code_churn_df_no_merge["repo_fk"] == url]
        repo_code_churn_num = repo_code_churn_df_no_merge["code_churn"].sum()

        print(repo_code_churn_num)
        print(repo_added_log_num + repo_deleted_log_num + 2*repo_updated_log_num)
        print(repo_added_log_num)
        print(repo_deleted_log_num)
        print(repo_updated_log_num)


def calculate_quantile(final_metrics: str):
    df = pd.read_csv(final_metrics)
    # print(type(df[df["log_churn_rate"]==0.030484]))
    print(df.log_churn_rate.quantile(.50))
    # print(df.log_churn_rate.quantile(.75))


def draw_histogram_plot(final_metrics: str):
    df = pd.read_csv(final_metrics)
    tmp = df['log_churn_rate'].to_list()
    # print(tmp)
    float_list = list(map(float, tmp))
    multiple_float_list = [i * 100 for i in float_list]
    # bins = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
    bins = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
    # bins = [0, 3500, 7000, 10500, 14000, 17500, 21000, 24500, 28000, 31500, 35000]
    hist, bins = np.histogram(multiple_float_list, bins=bins)
    # width = np.diff(bins)
    # center = (bins[:-1] + bins[1:]) / 2

    fig, ax = plt.subplots()
    # Plot the histogram heights against integers on the x axis
    ax.bar(range(len(hist)), hist, width=1)

    # Set the ticks to the middle of the bars
    ax.set_xticks([0.5 + i for i, j in enumerate(hist)])
    # ax.tick_params(axis='x', pad=45)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    # Set the xticklabels to a string that tells us what the bin edges were
    ax.set_xticklabels(['{}'.format(bins[i + 1]) for i, j in enumerate(hist)],)
    # plt.ylabel('Number of projects')
    # plt.xlabel('Log churn rate (%)')
    plt.xlim(xmin=-0.51)

    plt.xticks(fontsize=22, rotation=70)
    plt.yticks(fontsize=22)
    plt.show()
    # bins = [0, 700, 1000, 5000, 30000]
    # width = 0.7 * (bins[1] - bins[0])
    # center = (bins[:-1] + bins[1:]) / 2
    # plt.hist(tmp.to_list(), density=True, bins=bins)  # `density=False` would make counts
    # plt.ylabel('Probability')
    # plt.xlabel('Data')
    # print(len(tmp.index))
    # sns.distplot(df['log_density'], hist=True, kde=True,
    #              bins='auto', color='darkblue',
    #              hist_kws={'edgecolor': 'black'},
    #              kde_kws={'linewidth': 1}

    # plt.show()


def calculate_correlation(final_metrics: str):
    df = pd.read_csv(final_metrics)
    tmp = df['log_churn_rate'].to_list()
    float_churn_list = list(map(float, tmp))

    tmp1 = df['log_density'].to_list()
    float_density_list = list(map(float, tmp1))

    print(scipy.stats.pearsonr(float_churn_list, float_density_list))


def get_arithmetic_result_of_list(csv_path: str):
    df = pd.read_csv(csv_path)
    log_churn_list = df["log_churn_rate"].to_list()
    float_log_churn_list = list(map(float, log_churn_list))
    array = np.array(float_log_churn_list)
    quartile = np.percentile(array, np.arange(0, 101, 25))
    mean = np.mean(array)
    print('mean: {}, quartile: {}'.format(mean, quartile))


if __name__ == '__main__':
    # calculate_average_churn_rate("EXPORTED_CSV_PATH", "EXPORTED_CSV_PATH", "EXPORTED_CSV_PATH")
    # calculate_quantile("EXPORTED_CSV_PATH")
    # draw_histogram_plot("EXPORTED_CSV_PATH")
    # calculate_correlation("EXPORTED_CSV_PATH")
    # get_arithmetic_result_of_list("EXPORTED_CSV_PATH")
    pass




