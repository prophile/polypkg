# WARNING: HERE BE DRAGONS

import yaml
import os.path
import urllib.parse
import re
from copy import deepcopy

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

def clean_package(value):
    backup = deepcopy(value)
    if 'base' in value:
        old_base = value['base']
        del value['base']
        value['files'] = {fn: urllib.parse.urljoin(old_base, val) for fn, val in value['files'].items()}
    # Strip the github: URLs
    value['files'] = {fn: strip_github(url) for fn, url in value['files'].items()}
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

