# WARNING: HERE BE DRAGONS

import yaml
import os.path
import urllib.parse
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

def clean_package(value):
    backup = deepcopy(value)
    if 'base' in value:
        old_base = value['base']
        del value['base']
        value['files'] = {fn: urllib.parse.urljoin(old_base, val) for fn, val in value['files'].items()}
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

