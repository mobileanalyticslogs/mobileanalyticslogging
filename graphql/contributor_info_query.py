from graphql.git_query import GitQuery


class ContributorInfoQuery(GitQuery):
    def __init__(self, github_token, query, query_params):
        super(ContributorInfoQuery, self).__init__(github_token, query, query_params)

    def generator(self):
        while True:
            yield super().run_query()

    def iterator(self):
        generator = self.generator()
        has_next_page = True
        contributor_info_list = []
        while has_next_page:
            response = next(generator)
            end_cursor = response["data"]["repository"]["defaultBranchRef"]["target"]["history"]["pageInfo"][
                "endCursor"]
            self.query_params["after"] = end_cursor
            has_next_page = response["data"]["repository"]["defaultBranchRef"]["target"]["history"]["pageInfo"][
                "hasNextPage"]
            edges = response["data"]["repository"]["defaultBranchRef"]["target"]["history"]["edges"]
            contributor_info_list.extend(edges)

        return contributor_info_list
