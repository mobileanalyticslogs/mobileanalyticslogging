import os
import platform
import socket

from conf import config
from util.git_apm_grepper import GitApmGrepper


def main():
    conf_csv = '../data/api_search_result.csv'
    output_result_csv = '../data/analytics_repo_list.csv'

    apm_layout_configs = config.APM_LAYOUT_CONFIGS

    # Choose result output path according to testing environment
    project_out_dir = ''
    num_processors = 1
    if platform.system() == 'Darwin':
        project_out_dir = 'REPO_LOCAL_PATH'
        num_processors = os.cpu_count() - 1
    elif platform.system() == 'Linux':
        if socket.gethostname() in ['pinky', 'brain2']:
            # If on our server
            project_out_dir = 'CUSTOMIZED_PATH'
            num_processors = os.cpu_count() // 2
        else:
            # If on compute canada
            project_out_dir = 'CUSTOMIZED_PATH'
            num_processors = os.cpu_count()

    grepper = GitApmGrepper(conf_path=conf_csv, layout_config=apm_layout_configs, result_out_path=output_result_csv,
                            project_out_dir=project_out_dir)

    projects_info = grepper.projects

    jobs_process = []

    # Split projects into N chunks
    k, m = divmod(len(projects_info), num_processors)
    project_info_chunks = [projects_info[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(num_processors)]

    for proc_id in range(0, num_processors):
        jobs_process.append(
            grepper.start(projects=project_info_chunks[proc_id])
        )
        # util.start(projects=project_info_chunks[proc_id])

    [j.join() for j in jobs_process]


if __name__ == '__main__':
    # Test
    main()
