# Mobile Analytics Logging



### Get and filter repos

1. Execute run_api_crawler.py
2. Execute run_apm_grepper.py

### Data

The data about firebase analytics is in analytics_repo_list.csv

The target apps for analysis can be downloaded [here](https://drive.google.com/file/d/1LpXLDrw6H6wkXbl6cN7rmPMYgB-c1DfM/view?usp=sharing).

### Before running the program

1. Download and unzip the repos
2. Configure the database info and local repo path
3. Install the required libraries (requirements.txt)

### before analysing the data

1. Export to csv by using the query in config.py
2. Analyze with the corresponding functions in database_analyzer.py