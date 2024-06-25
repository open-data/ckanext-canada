#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Usage:
    openness_report.py --site <https://open.canada.ca/data>
                       --dump <openness_report.csv>
'''
import argparse
import os
import sys
import gzip
import requests
from io import BytesIO
import json
from collections import defaultdict

import unicodecsv
import codecs
from ckanext.canada.helpers import openness_score
from ckanext.scheming.plugins import SchemingDatasetsPlugin as p

import ckanapi

proxy= os.environ.get('http_proxy', '')


class Records():
    def __init__(self, site_url):
        self.site = ckanapi.RemoteCKAN(site_url)

        p.instance = p()
        p.instance._load_presets(config={'scheming.presets':"ckanext.canada:schemas/presets.yaml"})

    def download(self, verbose=False):
        # dataset https://open.canada.ca/data/en/dataset/c4c5c7f1-bfa6-4ff6-b4a0-c164cb2060f7
        ds = self.site.action.package_show(id='c4c5c7f1-bfa6-4ff6-b4a0-c164cb2060f7')
        url = None
        for res in ds['resources']:
            if res['url'][-3:] == '.gz':
                url = res['url']
                break
        assert(url)

        if verbose:
            print("Downloading records from %s" % url)

        r = requests.get(url, stream=True)
        zf = BytesIO(r.content)

        records = []
        try:
            with gzip.GzipFile(fileobj=zf, mode='rb') as fd:
                for line in fd:
                    records.append(json.loads(line.decode('utf-8')))
                    if len(records) >= 50:
                        yield (records)
                        records = []
            if len(records) >0:
                yield (records)
        except GeneratorExit:
            pass
        except:
            import traceback
            traceback.print_exc()
            print('error reading downloaded file')

    def details(self, csvfile, verbose=False):
        reports = defaultdict(list)
        for records in self.download(verbose=verbose):
            for record in records:
                id = record['id']
                score = openness_score(record)
                report = reports[record['organization']['title']]
                title = record["title_translated"]
                title = title.get('en', title.get('en-t-fr', '')) + ' | ' + title.get('fr', title.get('fr-t-en', ''))
                url = ''.join(['https://open.canada.ca/data/en/dataset/', id, ' | ',
                      'https://ouvert.canada.ca/data/fr/dataset/', id])
                report.append([title, url, score])

        if verbose:
            print("Dumping detailed openness ratings to %s" % csvfile)

        orgs = list(reports)
        orgs.sort()
        outf=open(csvfile, 'wb')
        outf.write(codecs.BOM_UTF8)
        out = unicodecsv.writer(outf)
        #Header
        out.writerow([
                      "Department Name Englist | Nom du ministère en français",
                      "Title English | Titre en français",
                      "URL",
                      "Openness Rating | Cote d'ouverture",
                    ])
        for k in orgs:
            rlist = reports[k]
            for r in rlist:
                line=[k, r[0], r[1], r[2]]
                out.writerow(line)
        outf.close()
        if verbose:
            print("Done!")

    def iter_resources(self, verbose=False):
        reports = defaultdict(lambda: defaultdict(int))
        for records in self.download(verbose=verbose):
            for record in records:
                score = openness_score(record)
                report = reports[record['organization']['title']]
                report[score] += 1
        self.reports = reports

    def dump(self, csvfile, verbose=False):
        if verbose:
            print("Dumping openness ratings to %s" % csvfile)
        outf=open(csvfile, 'wb')
        outf.write(codecs.BOM_UTF8)
        out = unicodecsv.writer(outf)
        #Header
        out.writerow([
                      "Department Name English / Nom du ministère en anglais",
                      "Department Name French / Nom du ministère en français",
                      "Openness report (score:count) / Rapport d'ouverture (score: compter)",
                    ])
        for k,v in self.reports.items():
            names = list(map(lambda x: x.strip(), k.split('|')))
            line=[names[0], names[1], dict(v)]
            out.writerow(line)
        outf.close()
        if verbose:
            print("Done!")

def main():
    parser = argparse.ArgumentParser(description='''portal records openness report''')
    parser.add_argument("--site", dest="site", required=True, help='''site gz file contains links.
                         download from https://open.canada.ca/static/od-do-canada.jl.gz.''')
    parser.add_argument("--detail", dest="detail",  action='store_true', default=False,
                        help="list each record")
    parser.add_argument("--dump", dest="dump", help="dump to csv file")
    parser.add_argument("--verbose", dest="verbose", action="store_true", default=False, help="increase verbosity")

    options = parser.parse_args()

    site = Records(options.site)
    if options.detail:
        return site.details(options.dump, options.verbose)

    site.iter_resources(options.verbose)
    if options.dump:
        site.dump(options.dump, options.verbose)
        return


if __name__ == '__main__':
    main()
    sys.exit(0)
