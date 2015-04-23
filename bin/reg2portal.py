#!/usr/bin/env python
"""
Script uploading input files from registry to portal via CKAN API.

Usage:
    reg2portal.py CKAN_INI_FILE PORTAL_URL API_KEY PACKAGE_ID FILE ...
"""

import ckanapi
from ckanapi.errors import CKANAPIError
import ConfigParser
from docopt import docopt
import os
import sys
import logging

usage = __doc__
opts = docopt(__doc__)

if len(opts) < 5:
    sys.stderr.write(opts + '\n')
    sys.exit()

ini_file = opts['CKAN_INI_FILE']
portal_url = opts['PORTAL_URL']
api_key = opts['API_KEY']
package_id = opts['PACKAGE_ID']
files = opts['FILE']

cfg = ConfigParser.ConfigParser()
cfg.read(opts['CKAN_INI_FILE'])

logging.config.fileConfig(opts['CKAN_INI_FILE'])
log = logging.getLogger('ckanext')

user_agent = None

# Set user-agent
try:
    reg_url = cfg.get('app:main', 'ckan.site_url')
    if reg_url:
        user_agent = 'ckanapi-uploader/1.0 (+{0:s})'.format(reg_url)
except ConfigParser.Error:
    log.warning('ckan.site_url not configured: specifying default user-agent')
    pass

# Instantiate remote ckanapi
portal_site = ckanapi.RemoteCKAN(
    portal_url,
    apikey=api_key,
    user_agent=user_agent)

# Patch package: add resources
try:
    portal_site.call_action(
        'package_patch',
        {'id': package_id, 'url': '', 'resources': []})
    log.info('Cleared resources from package_id [{0:s}]'.format(package_id))

    for file in files:
        resource_name = os.path.basename(file)
        with open(file) as f:
            rc = portal_site.call_action(
                'resource_create',
                {'package_id': package_id, 'url': '', 'name': resource_name},
                files={'upload': f})
        log.info('Uploaded resource [{0:s}] to package_id [{1:s}]'.format(
            resource_name,
            package_id))

except (AttributeError, ValueError, CKANAPIError, Exception) as e:
    log.error('Encountered {0:s}'.format(str(e)))
