# WARNING: HERE BE DRAGONS

import yaml
import os.path
import urllib.parse
import re
import getpass
import functools
from hammock import Hammock

from copy import deepcopy

RUN_UPGRADES = False

urllib.parse.uses_relative.append('github')
urllib.parse.uses_netloc.append('github')

with open('packages.yaml') as f:
    package_db = yaml.load(f)

def strip_prefix(prefix, url):
    for n in range(len(url) - 1, 0, -1):
        component = url[n:]
        joined = urllib.parse.urljoin(prefix, component)
        if joined == url:
            return component
    return url

GITHUB_URL = 'https://raw.githubusercontent.com/{user}/{project}/{branch}/{path}'

def strip_github(url):
    components = urllib.parse.urlparse(url)
    if components.scheme != 'github':
        return url
    match = re.match('^/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)/(.*)$', components.path)
    if match is None:
        raise ValueError('inscrutable github URL: {}'.format(url))
    return GITHUB_URL.format(user=match.group(1),
                             project=match.group(2),
                             branch='master',
                             path=match.group(3))

shared_github_auth = None
def github_auth():
    global shared_github_auth
    if shared_github_auth is None:
        username = input('Github username: ')
        password = getpass.getpass('Github password: ')
        shared_github_auth = (username, password)
    return shared_github_auth

GITHUB_API = Hammock('https://api.github.com')
@functools.lru_cache(maxsize=128)
def get_latest_release(user, project):
    endpoint = GITHUB_API.repos(user, project).tags
    data = endpoint.GET(auth=github_auth()).json()
    # accept only basic semantic versions
    data = [entry for entry in data if re.match(r'\d+\.\d+\.\d+', entry['name'])]
    if len(data) == 0:
        return None
    return data[0]['name']

def use_latest_release(url):
    match = re.match(r'https://raw\.githubusercontent\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)/([^/]+)/(.*)$', url)
    if match is None:
        return url
    # Get the latest release
    user = match.group(1)
    project = match.group(2)
    old_ref = match.group(3)
    path = match.group(4)
    # use the github API
    most_recent = get_latest_release(user, project)
    if most_recent is None:
        print("WARNING: cannot upgrade to a release for {}/{}, skipping".format(user, project))
        return url
    if old_ref != most_recent:
        print("Upgrading project {}/{} from {} to {}".format(user, project, old_ref, most_recent))
    return "https://raw.githubusercontent.com/{user}/{project}/{tag}/{path}".format(user=user, project=project, tag=most_recent, path=path)

def clean_package(value):
    backup = deepcopy(value)
    if 'base' in value:
        old_base = value['base']
        del value['base']
        value['files'] = {fn: urllib.parse.urljoin(old_base, val) for fn, val in value['files'].items()}
    # Strip the github: URLs
    value['files'] = {fn: strip_github(url) for fn, url in value['files'].items()}
    # Refuse 'master' from github, use a release
    if RUN_UPGRADES:
        value['files'] = {fn: use_latest_release(url) for fn, url in value['files'].items()}
    prefix = os.path.commonprefix(value['files'].values())
    if '/' not in prefix:
        return backup
    prefix = prefix[0:prefix.rindex('/')+1]
    if len(prefix) > 12:
        value['base'] = prefix
        value['files'] = {fn: strip_prefix(prefix, url) for fn, url in value['files'].items()}
    return value

package_db = {key: clean_package(value) for key, value in package_db.items()}

with open('packages.yaml', 'w') as f:
    yaml.dump(package_db, f, default_flow_style = False)

