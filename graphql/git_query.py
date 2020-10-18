import requests
from conf import config


# https://gist.github.com/gbaman/b3137e18c739e0cf98539bf4ec4366ad
class GitQuery:
    BASE_URL = config.BASE_URL

    def __init__(self, github_token, query, query_params):
        self.github_token = github_token
        self.query = query
        self.query_params = query_params

    @property
    def headers(self):
        default_headers = dict(
            Authorization=f"token {self.github_token}"
        )
        return {
            **default_headers,
        }

    def run_query(self):
        request = requests.post(GitQuery.BASE_URL, json={'query': self.query, 'variables': self.query_params},
                                headers=self.headers)
        if request.status_code == 200:
            return request.json()
        else:
            raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code,
                                                                                     self.query_params))
