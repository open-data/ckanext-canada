#!/usr/bin/env python3

import ckanapi
import sys
import time

retries = 0
while retries < 5:
    try:
        source = ckanapi.RemoteCKAN(sys.argv[1])
        pkg = source.action.package_show(id=sys.argv[2])
        print(' '.join([r['url'] for r in pkg.get('resources', [])
              if r['url'].endswith('.csv')]))
        sys.exit(0)
    except ckanapi.errors.CKANAPIError:
        retries += 1
        time.sleep(8)
sys.exit(-1)
