#!/usr/bin/env python
"""
Usage:
  datasets_by_orgs_report.py CKAN_URL MONTHS

Eg:
  datasets_by_orgs_report.py http://open.canada.ca/data 12 > report.csv
"""
import sys

from unicodecsv import DictWriter
import ckanapi
from docopt import docopt

UTF8_BOM = u'\uFEFF'.encode('utf-8')

def main():
    opts = docopt(__doc__)

    num_months = int(opts['MONTHS'])
    rc = ckanapi.RemoteCKAN(opts['CKAN_URL'],
        user_agent='datasets_by_orgs_report.py (ckanext-canada)')

    org_list = rc.action.organization_list(
        all_fields=True,
        include_dataset_count=True)

    orgs = {o['name']: o for o in org_list}
    months = []

    fieldnames = [u'id', u'title_en', u'title_fr', u'url', u'current_datasets']

    sys.stdout.write(UTF8_BOM)
    out = DictWriter(sys.stdout, fieldnames=fieldnames, encoding='utf-8')

    for o in org_list:
        out.writerow({
            'id': o['id'],
            'title_en': o['title'].split(' | ')[0],
            'title_fr': o['title'].split(' | ')[-1],
            'url': opts['CKAN_URL'].rstrip('/') + u'/organization/' + o['name'],
            'current_datasets': o['package_count']
            })


main()
