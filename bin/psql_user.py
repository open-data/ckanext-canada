#!/usr/bin/env python

import ConfigParser
import urlparse
import sys

c = ConfigParser.ConfigParser()
c.read(sys.argv[1])
url = c.get('app:main', 'sqlalchemy.url')

u = urlparse.urlparse(url)
print u.username
