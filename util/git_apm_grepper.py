import subprocess
import logging
import tarfile
import pandas as pd
from git import Repo
import os
import shutil
from multiprocessing.pool import ThreadPool
import sys

from conf import config

sys.path.append(os.path.realpath('..'))
from wrapper.async_wrapper import run_async_multiprocessing
# Example: https://api.github.com/search/repositories?q=stars:<=10000+language:java&sort=stars&order=desc&per_page=100&page=1

# Setup io lock
try:
    from readerwriterlock import rwlock
    lock = rwlock.RWLockWrite().gen_wlock()
except ImportError:
    from threading import Lock
    lock = Lock()


def _read_conf(conf_path):
    df_conf = pd.read_csv(conf_path)
    return list(df_conf['ProjectInfo'])


def _create_if_not_exist(p, isFile=False):
    if isFile:
        # Delete file if exist
        if os.path.isfile(p):
            os.remove(p)
        p = os.path.dirname(p)

    if not os.path.isdir(p):
        os.makedirs(p)


class GitApmGrepper:

    def __init__(self, conf_path, layout_config, result_out_path, project_out_dir, log_dir='../log'):
        self.projects = _read_conf(conf_path)
        self.layout_config = layout_config

        self.project_out_dir = project_out_dir
        _create_if_not_exist(project_out_dir)

        self.error_log_dir = log_dir
        _create_if_not_exist(log_dir)
        self.general_logger = logging.getLogger("GENERAL")
        logging.basicConfig(
            filename=os.path.join(log_dir, 'error.log'),
            level=logging.WARN,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%d-%b-%y %H:%M:%S')
        self.err_logger = logging.getLogger("GitGrepper")

        self.out_path = result_out_path
        _create_if_not_exist(result_out_path, isFile=True)

    def clone_repo(self, url, to_path):
        """
        Clone repo from github
        :param url:
        :param to_path:
        :return:
        """
        if not os.path.isdir(to_path):
            try:
                self.general_logger.info("Cloning {}".format(url))
                Repo.clone_from(
                    url=url,
                    to_path=to_path,
                    # branch='master', depth=1,
                    config='http.sslVerify=false'
                )
                return True
            except Exception as ex:
                self.err_logger.error('Fail to clone repo: {url}; {ex}; {msg}'.format(url=url, ex=ex._cause, msg=ex.stderr.replace('\n', ';')))
                return False


    @run_async_multiprocessing
    def start(self, projects):
        # Max 10 threads
        pool_thread = ThreadPool(processes=10)
        for repo_info in projects:
            #self.process_repo(repo_info)
            pool_thread.apply_async(self.process_repo, args=(repo_info,))
        pool_thread.close()
        pool_thread.join()

    def process_repo(self, repo_info):
        """
        Process each repository
        :param repo_info:
        :param output_dir:
        :return:
        """
        # Add :@ to bypass credential (won't ask, just report error)
        # This cases happen when remote repo is not found
        # https://stackoverflow.com/questions/44482990/preventing-gitpython-from-asking-for-credentials-when-trying-to-clone-a-non-exis
        url = 'https://:@github.com/{repo_info}.git'.format(repo_info=repo_info)
        to_path = os.path.join(self.project_out_dir, repo_info.replace('/', '_'))
        # Clone repo if not exist
        found = self.clone_repo(url=url, to_path=to_path)

        if found:
            res = []
            for logging_lib, layout_keywords in self.layout_config.items():
                for layout, keywords in layout_keywords.items():
                    # Search keywords
                    search_res = self.grepper(dir=to_path, pattern=keywords)

                    if search_res is not None:
                        res.append(
                            {
                                'ProjectInfo': repo_info,
                                'LoggingLibrary': logging_lib,
                                'Layout': layout,
                                'Keyword': ','.join(keywords),
                                'SearchResult': search_res
                            }
                        )

            # Write result
            if len(res) > 0:
                self.write_output(result=res)

            # Compress repo
            self.compress(target_dir=to_path)

    def write_output(self, result):
        """
        Output the result to dataframe
        :param result:
        :return:
        """
        df = pd.DataFrame()
        df = df.append(result, ignore_index=True)

        df = df.reindex(sorted(df.columns), axis=1)

        with lock:
            if os.path.isfile(self.out_path):
                df.to_csv(self.out_path, mode='a', index=False, header=False)
            else:
                df.to_csv(self.out_path, mode='w', index=False, header=True)

    def compress(self, target_dir):
        """
        Compress the processed project
        :param target_dir:
        :return:
        """
        tar = tarfile.open(target_dir + ".tar.gz", "w:gz")
        tar.add(target_dir, arcname=os.path.basename(target_dir))
        tar.close()
        shutil.rmtree(target_dir)

    def grepper(self, dir, pattern, include_ext=[], exclude_ext=[], ignore_case=True):
        """
        Grep keyword from a directory, return a list of qualified files
        Example: grep --include=\*.{c,h} -rnw '/path/to/somewhere/' -e "pattern"
        If ignoring case, add -i
        -l ignores the matched content output
        :param dir:
        :param kw:
        :return:
        """
        if isinstance(pattern, str):
            grep_cmd = 'grep -rnwil --binary-files=without-match {dir} -e "{pattern}"'.format(dir=dir, pattern=pattern)
        elif isinstance(pattern, list):
            grep_cmd = 'grep -rnwil --binary-files=without-match {dir} -e "{pattern}"'.format(dir=dir, pattern='\\|'.join(pattern))

        try:
            out = subprocess.check_output(grep_cmd, shell=True, encoding='utf-8')
            out = out.rstrip().replace(self.project_out_dir, '').split('\n')
        except Exception as e:
            # Not found
            out = None
        return out
