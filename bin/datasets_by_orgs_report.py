#!/usr/bin/env python
"""
Usage:
  datasets_by_orgs_report.py PORTAL_URL REGISTRY_URL MONTHS

Eg:
  datasets_by_orgs_report.py http://open.canada.ca/data \\
      http://registry.open.canada.ca 12 > report.csv
"""
import sys

from unicodecsv import DictWriter
import ckanapi
from docopt import docopt

UTF8_BOM = u'\uFEFF'.encode('utf-8')

def main():
    opts = docopt(__doc__)

    num_months = int(opts['MONTHS'])
    portal = ckanapi.RemoteCKAN(opts['PORTAL_URL'],
        user_agent='datasets_by_orgs_report.py (ckanext-canada)')
    registry = ckanapi.RemoteCKAN(opts['REGISTRY_URL'],
        user_agent='datasets_by_orgs_report.py (ckanext-canada)')

    sys.stderr.write('getting org list...\n')
    org_list = portal.action.organization_list(
        all_fields=True,
        include_dataset_count=True)

    sys.stderr.write('getting published datasets...\n')
    published_datasets = set(portal.action.package_list())

    orgs = {o['name']: o for o in org_list}
    months = []

    fieldnames = [
        u'id', u'title_en', u'title_fr', u'url', u'current_datasets']

    sys.stderr.write('collecting activities...\n')
    offset = 0


    sys.stdout.write(UTF8_BOM)
    out = DictWriter(sys.stdout, fieldnames=fieldnames, encoding='utf-8')

    for o in org_list:
        out.writerow({
            'id': o['id'],
            'title_en': o['title'].split(' | ')[0],
            'title_fr': o['title'].split(' | ')[-1],
            'url': opts['PORTAL_URL'].rstrip('/') 
                + u'/organization/' + o['name'],
            'current_datasets': o['package_count']
            })


main()
