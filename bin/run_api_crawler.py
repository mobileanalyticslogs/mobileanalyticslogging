from conf import config
from util.git_api_crawler import GitApiCrawler


def main():
    # Test
    input_api_csv = '../data/git_api_list.csv'

    api_keyword_configs = config.API_LAYOUT_CONFIGS
    # This part is reserved for remote crawling
    for logging_lib, layout_keywords in api_keyword_configs.items():
        for layout, keywords in layout_keywords.items():
            crawler = GitApiCrawler(conf_path=input_api_csv, logging_lib=logging_lib, keyword_layout=layout)
            crawler.start(keywords=keywords)


if __name__ == '__main__':
    main()