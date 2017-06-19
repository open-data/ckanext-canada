#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Usage:
    openness_report.py --file <od-do-canada.jl.gz> --format <presets.yaml>
                       --dump <openness_report.csv>
'''
import argparse
import os
import time
import datetime
import sys
import logging
import tempfile
import gzip
import json
import yaml
from collections import defaultdict

from functools import partial
import traceback
import unicodecsv
import codecs

proxy= os.environ['http_proxy']


class Records():
    def __init__(self, file, fmt_file):
        self.file = file
        if not os.path.isfile(self.file):
            self.file = None
        self.download_file = None
        with open(fmt_file, 'r') as f:
            presets = yaml.load(f)
        fmt = None
        for it in presets['presets']:
            if it['preset_name']=='canada_resource_format':
                fmt = it['values']['choices']
        if not fmt:
            raise Exception('no resource format loaded')
        self.fmt = filter(lambda x: 'openness_score' in x, fmt)

    def __delete__(self):
        if not self.file:
            if self.download_file:
                os.unlink(self.download_file)
                print('temp file deleted', self.download_file)

    def download(self):
        if not self.file:
            # dataset http://open.canada.ca/data/en/dataset/c4c5c7f1-bfa6-4ff6-b4a0-c164cb2060f7
            url='http://open.canada.ca/static/od-do-canada.jl.gz'
            r = requests.get(url, stream=True)

            f = tempfile.NamedTemporaryFile(delete=False)
            for chunk in r.iter_content(1024 * 64):
                    f.write(chunk)
            f.close()
            self.download_file = f.name

        records = []
        fname = self.file or f.name
        try:
            with gzip.open(fname, 'rb') as fd:
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


    def iter_resources(self):
        count = 0
        reports = defaultdict(lambda: defaultdict(int))
        for records in self.download():
            for record in records:
                report = reports[record['organization']['title']]
                formats = map(lambda x: x['format'], record['resources'])
                scores = map(lambda x:x['openness_score'],
                             filter(lambda x: x['value'] in formats,
                                    self.fmt))
                scores.append(1)
                score = max(scores)

                for r in record['resources']:
                    if 'data_includes_uris' in r.get('data_quality', []):
                        score = max(4, score)
                        if 'data_includes_links' in r.get('data_quality', []):
                            score = max(5, score)
                report[score] += 1
        self.reports = reports

    def dump(self, csvfile):
        outf=open(csvfile, 'wb')
        outf.write(codecs.BOM_UTF8)
        out = unicodecsv.writer(outf)
        #Header
        out.writerow([
                      "Department Name English / Nom du ministère en anglais",
                      "Department Name French / Nom du ministère en français",
                      "Openness report (score:count) / Rapport d'ouverture (score: compter)",
                    ])
        for k,v in self.reports.iteritems():
            names = map(lambda x: x.strip(), k.split('|'))
            line=[names[0], names[1], dict(v)]
            out.writerow(line)
        outf.close()



def main():
    parser = argparse.ArgumentParser(description='''portal records openness report''')
    parser.add_argument("--file", dest="file", required=True, help='''site gz file contains links.
                         download from http://open.canada.ca/static/od-do-canada.jl.gz.''')
    parser.add_argument("--format", dest="fmt", required=True, help="format presets")
    parser.add_argument("--dump", dest="dump", help="dump to csv file")

    options = parser.parse_args()

    site = Records(options.file, options.fmt)
    site.iter_resources()
    if options.dump:
        site.dump(options.dump)
        return


if __name__ == '__main__':
    main()
    sys.exit(0)
