#!/usr/bin/env python
"""
Usage:

datasets_by_orgs_report.py CKAN_URL MONTHS

Eg:

datasets_by_orgs_report.py http://open.canada.ca/data 12
"""

import ckanapi
from docopt import docopt

def main():
    opts = docopt()

    rc = ckanapi.RemoteCKAN(opts['CKAN_URL'],
        user_agent='datasets_by_orgs_report.py (ckanext-canada)')

    orgs = rc.action.organization_list(all_fields=True)

    import pdb; pdb.set_trace()
