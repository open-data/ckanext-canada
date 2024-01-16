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

from unicodecsv import writer
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
    processed = 0

    sys.stderr.write('collecting activities...\n')
    sys.stderr.write(ym_head(months[-1]) + u':')
    for act in activities(registry):
        y, m = act['timestamp'][:7].split('-')
        act_ym = int(y), int(m)
        if act_ym != months[-1]:
            while len(months) < num_months:
                months.append(prior_month(months[-1]))
                for c in counts:
                    counts[c].append(0)
                sys.stderr.write(str(processed) + u'\n'
                    + ym_head(months[-1]) + u':')
                processed = 0
                if months[-1] == act_ym:
                    break
            else:
                sys.stderr.write(u'all months collected.\n')
                break

        if 'package' not in act['data']:
            continue
        if act['object_id'] not in published_datasets:
            continue
        owner_org = act['data']['package'].get('owner_org')
        if owner_org not in counts:
            continue

        act_type = act['activity_type']
        if act_type == 'new package':
            counts[owner_org][-1] += 1
        elif act_type == 'deleted package':
            counts[owner_org][-1] -= 1
        processed += 1
    sys.stderr.write(str(processed) + u'\n')

    fieldnames = [
        u'id', u'title_en', u'title_fr', u'url', u'current_datasets',
        ] + [ym_head(ym) for ym in months]

    sys.stdout.write(UTF8_BOM)
    out = writer(sys.stdout, encoding='utf-8')
    out.writerow(fieldnames)

    for o in org_list:
        out.writerow([
            o['id'],
            o['title'].split(' | ')[0],
            o['title'].split(' | ')[-1],
            opts['PORTAL_URL'].rstrip('/')
                + u'/organization/' + o['name'],
            o['package_count']
            ] + counts[o['id']])


def prior_month(ym):
    y, m = ym
    if m == 1:
        return y - 1, 12
    return y, m - 1


def ym_head(ym):
    return u'%04d-%02d' % ym


def activities(registry):
    offset = 0

    while True:
        batch = registry.action.recently_changed_packages_activity_list(
            offset=offset, limit=1000)
        if not batch:
            break
        for act in batch:
            yield act
        offset += len(batch)
    sys.stderr.write(u'activity list ended at %d\n' % offset)

main()
