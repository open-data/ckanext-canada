#!/usr/bin/env python

import ConfigParser
import urlparse
import sys

c = ConfigParser.ConfigParser()
c.read(sys.argv[1])
url = c.get('app:main', 'sqlalchemy.url')

u = urlparse.urlparse(url)
print 'PGPASSWORD=' + u.password,
print 'psql',
print '-d', u.path.lstrip('/'),
print '-p', u.port or '5432',
print '-U', u.username,
