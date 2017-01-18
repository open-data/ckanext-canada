#!/usr/bin/env python
"""
Usage:
  datasets_by_orgs_report.py PORTAL_URL REGISTRY_URL MONTHS

Eg:
  datasets_by_orgs_report.py http://open.canada.ca/data \\
      http://registry.open.canada.ca 12 > report.csv
"""
import sys
from datetime import datetime

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

    orgs = {o['id']: o for o in org_list}
    now = datetime.utcnow()
    months = [(now.year, now.month)]
    counts = {o['id']: [0] for o in org_list}

    sys.stderr.write('collecting activities...\n')
    for act in activities(registry):
        y, m = act['timestamp'][:7].split('-')
        act_ym = int(y), int(m)
        if act_ym != months[-1]:
            while len(months) <= num_months:
                months.append(prior_month(months[-1]))
                for c in counts:
                    counts[c].append(0)
                if months[-1] == act_ym:
                    break
            else:
                break

        if act['object_id'] not in published_datasets:
            continue
        if act.get('owner_org') not in counts:
            continue

        act_type = act['activity_type']
        if act_type == 'new package':
            counts[act['owner_org']][-1] += 1
        elif act_type == 'deleted package':
            counts[act['owner_org']][-1] -= 1

    fieldnames = [
        u'id', u'title_en', u'title_fr', u'url', u'current_datasets']

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


def prior_month(ym):
    y, m = ym
    if m == 1:
        return y - 1, 12
    return y, m - 1


def activities(registry):
    offset = 0

    while True:
        batch = registry.action.recently_changed_packages_activity_list(
            offset=offset)
        if not batch:
            return
        for act in batch:
            yield act
        offset += len(batch)

main()
