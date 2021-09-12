import git
import time
import requests
from elasticsearch import Elasticsearch
import json
import time
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


doc_id = 1
es = Elasticsearch()
repo_name = 'rockstar'

try:
  my_repo = git.Repo.clone_from('https://github.com/RockstarLang/rockstar', repo_name)
except git.exc.GitCommandError:
  my_repo = git.Repo(repo_name)

count = my_repo.git.rev_list('--count', 'HEAD')


github_rate_limit = 10
number_of_pages = int(count)/github_rate_limit
record_count = 0

for each_page in range(int(number_of_pages)):
  my_commits = list(my_repo.iter_commits('master', max_count=10, skip=record_count))
# my_commits = my_repo.iter_commits('master', max_count=count)

  for i in my_commits:
    email = i.author.email
    url = 'https://api.github.com/search/users?q=' + email
    x = requests.get(url, verify=False)

    try:
      github_items = x.json()['items']
      if len(github_items) <= 0:
        print('This user email does not exist or email changed:')
        print(i.author.email)
        continue
      github_username = x.json()['items'][0]['login']
    except x.status_code == 403:
      if 'API rate limit exceeded for' in x.json()['message']:
        print("""API rate limit exceeded. (But here's the good news: Authenticated requests get a higher rate limit. 
        Check out the documentation for more details.)\",
        'documentation_url': 'https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting'""")
        break

    user_info_url = 'https://api.github.com/users/' + github_username
    y = requests.get(user_info_url, verify=False)
    github_account_created_at = y.json()['created_at']

    dict = { 'commited_at': time.strftime("%a, %d %b %Y %H:%M", time.gmtime(i.committed_date)),
              'committed_by': i.author.name,
              'commit_message': i.message,
              'account_created_at': github_account_created_at
    }
    res = es.index(index="commit-history", id=doc_id, body=dict)
    doc_id += 1
    print(res['result'])

    time.sleep(60)
    record_count += github_rate_limit


# considerations:
# The github API has rate limiting for both authenticated and unauthenticated users.
# The github Search API also has its own separate rate limiting which is way smaller than the default API
# 10 requests per minute and 30 requests per minute for unauthenticated and authenticated users respectively.

# you should have elasticsearch and kibana either installed or you can use hosted options
# this script makes use of the mac versions of these 2. so basically they are running
# on localhost.