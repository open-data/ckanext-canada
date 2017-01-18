#!/usr/bin/env python

import ckanapi
import sys

source = ckanapi.RemoteCKAN(sys.argv[1])
pkg = source.action.package_show(id=sys.argv[2])
print ' '.join([r['url'] for r in pkg.get('resources', [])
    if r['url'].endswith('.csv')])
