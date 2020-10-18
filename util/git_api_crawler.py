import subprocess
import time
import sys
import json
import logging
import requests
import pandas as pd
from stem import Signal
from stem.control import Controller
import os

os.chdir(os.path.realpath('.'))
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
    return list(df_conf['owner_repo'])


def restart_tor(sleep_time=5):
    print('All ports used, restarting Tor...')
    # cmd_restart = 'killall -HUP tor | /etc/init.d/tor start'
    cmd_restart = 'pkill -f tor | /etc/init.d/tor start'
    subprocess.Popen(cmd_restart, shell=True).wait()
    time.sleep(sleep_time)


def change_ip_address(port_num):
    print('Switching port from %d to %d' % (port_num, port_num + 10))
    time.sleep(1)
    try:
        with Controller.from_port(port=port_num + 10) as controller:
            # Add to torrc before
            controller.authenticate('abc')
            controller.signal(Signal.NEWNYM)
    except Exception:
        print('[EXCEPTION]', sys.exc_info()[0], flush=True)


def write_result(results, filename):
    """
    Append or create dataframe to output csv
    :param results:
    :param filename:
    :return:
    """
    df = pd.DataFrame()
    df = df.append(results, ignore_index=True)

    df = df.reindex(sorted(df.columns), axis=1)

    if os.path.isfile(filename):
        df.to_csv(filename, sep=',', mode='a', encoding='utf-8', index=False, header=False)
    else:
        df.to_csv(filename, sep=',', mode='w', encoding='utf-8', index=False, header=True)


class GitApiCrawler:

    def __init__(self, conf_path, logging_lib, keyword_layout, error_log_dir='../log'):
        self.projects = _read_conf(conf_path)
        self.logging_lib = logging_lib
        self.layout = keyword_layout
        self.error_log_dir = os.path.abspath(error_log_dir)
        if not os.path.isdir(self.error_log_dir):
            os.makedirs(error_log_dir)
        logging.basicConfig(filename=os.path.join(error_log_dir, 'error.log'), level=logging.WARN)
        self.logger = logging.getLogger("GitCrawler")

    def add_to_list(self, keyword, repo_info, port_num=9050):

        # time.sleep(1)

        proxies = {
            'http': 'socks5h://127.0.0.1:{port_num}'.format(port_num=port_num),
            'https': 'socks5h://127.0.0.1:{port_num}'.format(port_num=port_num)
        }
        url = 'https://api.github.com/search/code?q={keyword}+in:file+repo:{repo_info}'.format(
            keyword=keyword, repo_info=repo_info)

        # If error, run pip install pysocks
        try:
            response = requests.get(url, timeout=10, allow_redirects=False, proxies=proxies)
        except Exception:
            # Most likely to be connection error, restart Tor
            # Give it a longer wait time
            restart_tor(sleep_time=10)
            return self.add_to_list(keyword=keyword, repo_info=repo_info, port_num=9050)

        # response = requests.get(url, timeout=10, allow_redirects=False)

        # cmd = "curl --proxy socks5h://localhost:9050 'https://api.github.com/search/code?q={keyword}+in:file+repo:{username}/{projectname}'".format(
        #     keyword=keyword, username=username, projectname=projectname
        # )
        # proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        # response, err = proc.communicate()
        ##print(out)

        res_list = []
        try:
            # out = json.loads(response.decode('utf-8'))
            out = json.loads(response.text)

            for item in out['items']:
                res_dict = \
                    {'repo_info': repo_info,
                     'keyword': keyword,
                     'path': item['path'],
                     'url': item['url'],
                     'git_url': item['git_url']}
                res_list.append(res_dict)

            print('Read: [{layout_info}] [{repo_info}]'.format(
                layout_info='-'.join([self.logging_lib, self.layout, keyword]), repo_info=repo_info))

            return res_list, port_num

        except KeyError as e:
            # Not found, probably not match
            if response.status_code == 422:
                self.logger.error('[422] [Deprecated] KeyError in searching url: %s' % url)

                # Write error message
                error_json_dir = os.path.join(self.error_log_dir, 'err_json')
                if not os.path.isdir(error_json_dir):
                    os.makedirs(error_json_dir)
                with open(os.path.join(error_json_dir,
                                       '[%d]%s.json' % (response.status_code, repo_info.replace('/', '_'))), 'w') as wj:
                    wj.write(response.text)
                wj.close()
                print('Error in %s, probably deprecated' % repo_info)
                return [], port_num

            elif response.status_code == 403:
                print("Detected, change ip now")
                # If exceed maximum allowed
                # If port number in selected range
                if port_num in range(9050, 9241):
                    # self.change_ip_address(port_num=port_num)
                    return self.add_to_list(keyword=keyword, repo_info=repo_info, port_num=port_num + 10)
                else:
                    restart_tor()
                    return self.add_to_list(keyword=keyword, repo_info=repo_info, port_num=9050)
            else:
                self.logger.error('[%d] [Unknown] KeyError in searching url: %s' % (response.status_code, url))
                # Write error message
                error_json_dir = os.path.join(self.error_log_dir, 'err_json')
                if not os.path.isdir(error_json_dir):
                    os.makedirs(error_json_dir)
                with open(os.path.join(error_json_dir,
                                       '[%d]%s.json' % (response.status_code, repo_info.replace('/', '_'))), 'w') as wj:
                    wj.write(response.text)
                wj.close()
                return [], port_num

    def start(self, keywords, output_dir='../data/'):

        results = []
        port_num = 9050

        count = 200

        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        api_output_file = os.path.join(
            output_dir, 'api_search_result.csv')

        for repo_info in self.projects:

            for kw in keywords:

                # If all ports used, restart
                if port_num not in range(9050, 9241):
                    restart_tor()

                res, port_num = self.add_to_list(keyword=kw, repo_info=repo_info, port_num=port_num)
                results += res

                # count += 1
                # # Restart Tor at around every 10 requests
                # if count % 10 == 0:
                #     self.restartTor()

                # Write every 200 lines
                while count % 200 == 0:
                    write_result(results=results, filename=api_output_file)
                    results = []

        if len(results) > 0:
            write_result(results=results, filename=api_output_file)
            del results
