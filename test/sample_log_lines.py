import random
import pandas as pd


random_list = random.sample(range(1, 1344), 300)
df = pd.read_csv('../data/analytics_logging_lines.csv')
sample_df = df.sample(n=300)
sample_df.to_csv('../data/sampled_logging_lines_for_review.csv')
# print(sample_df.head(300))
