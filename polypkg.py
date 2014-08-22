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
from urllib.request import urlretrieve
import os
import os.path
import shutil
import sys
import yaml

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

def install_by_name(pkg_db, name):
    try:
        package = pkg_db[name]
    except KeyError:
        print('Unknown package: {}'.format(name), file=sys.stderr)
        return
    for dependency in package.get('dependencies', ()):
        if not os.path.exists(os.path.join('components', dependency)):
            install_by_name(pkg_db, dependency)
    print('Installing package {}...'.format(name))
    base = os.path.join('components', name)
    if os.path.exists(base):
        print('Removing previous install...', file=sys.stderr)
        shutil.rmtree(base)
    os.makedirs(base)
    for fn, source in package['files'].items():
        path = os.path.join(base, fn)
        print('  Installing {}'.format(fn), file=sys.stderr)
        urlretrieve(source, path)

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

