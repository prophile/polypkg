#!/usr/bin/env python3
"""
Sensible Polymer component database.

Usage:
  polypkg [options] <component>

Options:
  -h --help         Show this screen.
  --version         Show version.
  --database <db>   Load a custom package database.
"""
from collections.abc import Mapping
from docopt import docopt
import urllib.request as rq
import os
import os.path
import shutil
import sys
import yaml
import html.parser
import re

DEFAULT_DATABASE = os.path.join(os.path.dirname(__file__),
                                'packages.yaml')
VERSION = '0.0.1'
GITHUB_URL = 'https://raw.githubusercontent.com/{user}/{project}/{branch}/{path}'

# Github URL handler
class Github(rq.BaseHandler):
    def github_open(self, req):
        match = re.match(r'^/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)/(.+)$', req.selector)
        if not match:
            raise ValueError('Match failed on github path {}'.format(req.selector))
        user = match.group(1)
        project = match.group(2)
        path = match.group(3)
        branch = 'master'
        full_url = GITHUB_URL.format(**locals())
        return rq.urlopen(full_url)

opener = rq.build_opener(Github())
rq.install_opener(opener)

class PackageDatabase(Mapping):
    def __init__(self):
        self.packages = {}

    def load(self, fn):
        with open(fn) as f:
            self.packages.update(yaml.load(f))

    def __getitem__(self, key):
        return self.packages[key]

    def __iter__(self):
        return iter(self.packages)

    def __len__(self):
        return len(self.packages)

class DependenciesParser(html.parser.HTMLParser):
    def __init__(self, dependency, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dependency = dependency

    def handle_starttag(self, tag, attrs):
        if tag != 'link':
            return
        attrs = dict(attrs)
        if attrs.get('rel') != 'import':
            return
        match = re.match(r'^\.\./([a-zA-Z0-9_-]+)/.*$', attrs.get('href', ''))
        if match is None:
            return
        self.dependency(match.group(1))

def get_dependencies(path):
    deps = set()
    parser = DependenciesParser(deps.add)
    with open(path) as f:
        parser.feed(f.read())
    parser.close()
    return iter(deps)

def install_by_name(pkg_db, name):
    try:
        package = pkg_db[name]
    except KeyError:
        print('Unknown package: {}'.format(name), file=sys.stderr)
        return
    print('Installing package {}...'.format(name))
    base = os.path.join('components', name)
    if os.path.exists(base):
        print('Removing previous install...', file=sys.stderr)
        shutil.rmtree(base)
    os.makedirs(base)
    dependencies = []
    for fn, source in package['files'].items():
        path = os.path.join(base, fn)
        print('  Installing {}'.format(fn), file=sys.stderr)
        rq.urlretrieve(source, path)
        if fn.endswith('.html'):
            # parse for import links
            dependencies.extend(get_dependencies(path))
    for dependency in dependencies:
        if not os.path.exists(os.path.join('components', dependency)):
            install_by_name(pkg_db, dependency)

def main():
    options = docopt(__doc__, version=VERSION)
    pkg_db = PackageDatabase()
    pkg_db.load(DEFAULT_DATABASE)
    if options['--database'] is not None:
        pkg_db.load(options['--database'])
    name = options['<component>']
    install_by_name(pkg_db, name)

if __name__ == '__main__':
    main()

