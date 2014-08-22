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
import httplib2
import os
import os.path
import shutil
import sys
import yaml
import html.parser
import re
import urllib.parse
from urllib.parse import urljoin
from urllib.request import urlretrieve
from termcolor import cprint, colored

DEFAULT_DATABASE = os.path.join(os.path.dirname(__file__),
                                'packages.yaml')
VERSION = '0.0.1'

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
        attrs = dict(attrs)
        if tag == 'link':
            if attrs.get('rel') != 'import':
                return
            match = re.match(r'^\.\./([a-zA-Z0-9_-]+)/.*$', attrs.get('href', ''))
            if match is None:
                return
            self.dependency(match.group(1))
        elif tag == 'script':
            match = re.match(r'^\.\./([a-zA-Z0-9_-]+)/.*$', attrs.get('src', ''))
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

http_engine = None
def get(url, output):
    try:
        response, content = http_engine.request(url)
        if response.status == 200:
            with open(output, 'wb') as f:
                f.write(content)
        else:
            raise KeyError('Could not retrieve {}, code={}'.format(url, response.status))
    except httplib2.RelativeURIError:
        urlretrieve(url, output)

def install_by_name(pkg_db, name, missing_dep=lambda x: None):
    try:
        package = pkg_db[name]
    except KeyError:
        cprint('Unknown package: {}'.format(name), 'red', attrs=['bold'], file=sys.stderr)
        missing_dep(name)
        return
    print('Installing package {}...'.format(colored(name, 'blue')))
    base = os.path.join('components', name)
    if os.path.exists(base):
        print('Removing previous install...', file=sys.stderr)
        shutil.rmtree(base)
    os.makedirs(base)
    dependencies = []
    for fn, source in package['files'].items():
        fn_dir = os.path.dirname(fn)
        if fn_dir != '':
            real_fn_dir = os.path.join(base, fn_dir)
            if not os.path.exists(real_fn_dir):
                os.makedirs(real_fn_dir)
        path = os.path.join(base, fn)
        print('  {} {}'.format(colored('•', 'green'), fn), file=sys.stderr)
        get(urljoin(package.get('base', '.'), source), path)
        if fn.endswith('.html'):
            # parse for import links
            dependencies.extend(get_dependencies(path))
    for dependency in dependencies:
        if not os.path.exists(os.path.join('components', dependency)):
            install_by_name(pkg_db, dependency, missing_dep=missing_dep)

def main():
    global http_engine
    options = docopt(__doc__, version=VERSION)
    COMPONENT_CACHE = '/tmp/.polypkg-component-cache'
    if not os.path.exists(COMPONENT_CACHE):
        os.makedirs(COMPONENT_CACHE)
    http_engine = httplib2.Http(COMPONENT_CACHE)
    pkg_db = PackageDatabase()
    pkg_db.load(DEFAULT_DATABASE)
    if options['--database'] is not None:
        pkg_db.load(options['--database'])
    name = options['<component>']
    missing_deps = set()
    install_by_name(pkg_db, name, missing_dep=missing_deps.add)
    if missing_deps:
        cprint("MISSING DEPENDENCIES", 'red', attrs=['bold'], file=sys.stderr)
        for dep in missing_deps:
            cprint(" • {}".format(dep), 'red', file=sys.stderr)
        exit(1)

if __name__ == '__main__':
    main()

