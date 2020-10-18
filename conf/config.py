import platform

API_LAYOUT_CONFIGS = {
        'Firebase': {
            'Firebase': ['Firebase']
        },
    }

APM_LAYOUT_CONFIGS = {
        'Firebase': {
            'FirebaseAnalytics': ['FirebaseAnalytics']
        },
    }

REPO_INFO_QUERY = '''
    query($owner: String!, $name: String!, $after: String) { 
        repository(owner: $owner, name: $name){
            defaultBranchRef {
                target {
                    ... on Commit {
                        id
                            history(first: 100, after: $after) {
                                pageInfo {
                                    hasNextPage
                                    endCursor
                                }
                                edges {
                                    node {
                                        oid
                                        author {
                                            name
                                            email
                                            date
                                        }
                                    }
                                }
                            totalCount
                        }
                    }
                }
            }
        }
    }
'''
BASE_URL = 'https://api.github.com/graphql'
GITHUB_TOKEN = "PERSONAL_GITHUB_TOKEN"

# Database
DB_NAME = 'dbname'
DB_USER = 'username'
DB_PASSWORD = ''
DB_HOST = '127.0.0.1'
DB_PORT = 5432

APM_REPO_PATH = "REPO_TO_ANALYZE"

XML_PRE_STRING = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><unit xmlns="http://www.srcML.org/srcML/src" revision="1.0.0" language="Java" filename="code_temp.java">'

TEMP_FILE_PATH = "TEMP_FILE_PATH"

REPO_INFO_CSV_PATH = '../data/app_analytics_class_keyword.csv'

LEVENSHTEIN_RATIO_THRESHOLD = 0.5

QUERY_TO_EXPORT_CSV_FROM_DB = "\copy (select commit.repo_fk, commit.commit_id,commit.is_merge_commit, commit.code_churn, log.file_path, log.change_type, log.content, log.content_update_from from log join commit on commit.id = log.commit_fk) to EXPORTED_CSV_PATH csv header;"

def get_cloc_command():
    # Execute on local computer
    if platform.system() == 'Darwin':
        cloc_command = "cloc"
    else:
        cloc_command = "CLOC_PATH_ON_SERVER"

    return cloc_command
