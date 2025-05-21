#!/usr/bin/env python3

import argparse
import os
import time
import sys
import tempfile
import gzip
import json
from collections import defaultdict

import lmdb

import requests
import asyncio
import concurrent.futures

from functools import partial
from requests.models import Response
import urllib
import socket
from urllib.request import urlopen
import traceback
import unicodecsv
import codecs

proxy = os.environ['http_proxy']
temp_db = '/tmp/od_linkcheker2.db'
USER_AGENT = "open.canada.ca dataset link checker;"
URL_TIMEOUT = 20

''' Check the resource links of datasets on open.canada.ca
dataset http://open.canada.ca/data/en/dataset/c4c5c7f1-bfa6-4ff6-b4a0-c164cb2060f7
url='http://open.canada.ca/static/od-do-canada.jl.gz'
'''


def test_ftp(url):
    res = Response()
    try:
        req = urllib.request.Request(url)
        if proxy:
            req.set_proxy(proxy, 'http')
        response = urlopen(req, timeout=URL_TIMEOUT)
        chunk = response.read(16)
        if len(chunk) == 16:
            res.status_code = 200
        else:
            res.status_code = 404
    except Exception as e:
        print('ftp exception', url)
        return e
    print(url, res.status_code)
    return res


def get_a_byte(response, *args, **kwargs):
    if response.status_code == requests.codes.ok:
        count = 0
        for line in response.iter_content():
            count += (len(line))
            if count > 0:
                print(response.url, count)
                response.close()
                break


@asyncio.coroutine
def test_urls(urls, results):
    loop = asyncio.get_event_loop()
    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as e:
        for url in urls:
            if url[:6].lower() == 'ftp://':
                future = loop.run_in_executor(e, test_ftp, url)
            else:
                future = loop.run_in_executor(
                    e, partial(requests.get, headers={"user-agent": USER_AGENT},
                               hooks={'response': get_a_byte}, verify=False,
                               timeout=URL_TIMEOUT, stream=True),
                    url)
            futures.append(future)
    for future in futures:
        try:
            res = yield from future
        except requests.exceptions.ProxyError:
            print('proxy error', urls[futures.index(future)])
            res = Exception()
        except (requests.exceptions.ReadTimeout,
                requests.packages.urllib3.exceptions.MaxRetryError,
                requests.exceptions.ConnectTimeout,
                requests.packages.urllib3.exceptions.ConnectTimeoutError,
                socket.timeout):
            print('timeout', urls[futures.index(future)])
            res = Exception()
        except (requests.exceptions.InvalidSchema,
                requests.exceptions.InvalidURL):
            print('invalidURL', urls[futures.index(future)])
            res = Response()
            res.status_code = 404
        except Exception:
            traceback.print_exc()
            res = Exception()
        results.append(res)


class Records():
    def __init__(self, file, quick):
        self.file = file
        if not os.path.isfile(self.file):
            self.file = None
        self.download_file = None
        self.quick = quick
        mapsize = 100 * 1024 * 1024 * 1024
        self.env = lmdb.open(temp_db, map_size=mapsize, sync=False)

    def __delete__(self):
        self.env.close()
        if not self.file:
            if self.download_file:
                os.unlink(self.download_file)
                print('temp file deleted', self.download_file)

    def download(self):
        if not self.file:
            # dataset
            # /data/en/dataset/c4c5c7f1-bfa6-4ff6-b4a0-c164cb2060f7
            url = 'http://open.canada.ca/static/od-do-canada.jl.gz'
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
            if len(records) > 0:
                yield (records)
        except GeneratorExit:
            pass
        except Exception:
            traceback.print_exc()
            print('error reading downloaded file')

    def test_links(self, new_url, urls):
        links = []
        results = []
        for k, v in new_url.items():
            links.append(k)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_urls(links, results))
        with self.env.begin(write=True) as txn:
            now = time.time()
            results = zip(links, results)
            for url, response in results:
                if type(response) is Exception:
                    res = {'timestamp': now,
                           'status': -1,
                           'resources': new_url[url]}
                else:
                    try:
                        res = {'timestamp': now,
                               'status': response.status_code}
                        if response.status_code != requests.codes.ok:
                            res['resources'] = new_url[url]
                            res['org'] = urls.get(url, None)
                    except AttributeError:
                        res = {'timestamp': now,
                               'status': -1,
                               'resources': new_url[url]}

                txn.put(url.encode('utf-8'), json.dumps(res).encode('utf-8'))
        if links:
            time.sleep(5)

    def get_resources(self):
        count = 0
        new_url = defaultdict(list)
        urls = {}
        for records in self.download():
            now = time.time()
            count += len(records)
            with self.env.begin() as txn:
                for record in records:
                    id = record['id']
                    for res in record['resources']:
                        if (not res['url_type']) and res.get('url'):
                            url = res['url']
                            details = txn.get(url.encode('utf-8'))
                            if details:
                                details = json.loads(details.decode('utf-8'))
                                # short re-run test
                                if (
                                  self.quick and
                                  now - details.get('timestamp', 0) < 34 * 3600):
                                    if (
                                      details['status'] == requests.codes.ok or
                                      details['status'] == 404):
                                        continue
                            new_url[url].append('/'.join([id, res['id']]))
                            if record.get('organization'):
                                urls[url] = {'name': record['organization']['name'],
                                             'title': record['organization']['title']}
            if len(new_url) >= 5000:
                self.test_links(new_url, urls)
                new_url = defaultdict(list)
                urls = {}
        if new_url:
            self.test_links(new_url, urls)
        print('total record count: ', count)

    def dumpBrokenLink(self, csvfile):
        outf = open(csvfile, 'wb')
        outf.write(codecs.BOM_UTF8)
        out = unicodecsv.writer(outf)
        # Header
        out.writerow([
            'English URL / URL en anglais',
            'French URL / URL en français',
            'Metadata Record Portal Type / '
            'Type de portail de la record de métadonnées',
            'Metadata Record Name English / '
            'Nom de la record de la métadonnées anglais',
            'Metadata Record Name French / '
            'Nom de la record de la métadonnées français',
            "Department Name English / Nom du ministère en anglais",
            "Department Name French / Nom du ministère en français",
            "Resource Name English/ Nom de la resource en angalis",
            "Resource Name French/ Nom de la resource en français",
            "Broken Link / Lien brisé",
            "Status / Statut",
        ])
        data = {}
        with self.env.begin() as txn:
            for url, value in txn.cursor():
                details = json.loads(value.decode('utf-8'))
                if details['status'] != requests.codes.ok:
                    for res_id in details['resources']:
                        data[res_id] = {'status': details['status']}

        for records in self.download():
            for record in records:
                id = record['id']
                for res in record['resources']:
                    if not res['url_type'] and res.get('url'):
                        url = res['url']
                        full_id = '/'.join([id, res['id']])
                        detail = data.get(full_id, None)
                        if not detail:
                            continue
                        time_str = res.get('last_modified')
                        if not time_str:
                            time_str = res.get('created')
                        detail.update({
                            'url_en': '/'.join(
                                ['http://open.canada.ca/data/en/dataset',
                                 id,
                                 'resource',
                                 res['id']]),
                            'url_fr': '/'.join(
                                ['http://open.canada.ca/data/fr/dataset',
                                 id,
                                 'resource',
                                 res['id']]),
                            'portal_type': record['type'],
                            'record_name_en': record['title_translated']['en'],
                            'record_name_fr': record['title_translated']['fr'],
                            'org_name_en':
                                record['organization']['title'].split('|')[0],
                            'org_name_fr':
                                record['organization']['title'].split('|')[-1],
                            'name_en': res['name_translated']['en'],
                            'name_fr': res['name_translated']['fr'],
                            'link': url})

        # write to csv
        count, count2 = 0, 0
        portal_type_dict = {
            'dataset': "Open Data / Données ouvertes",
            'info': "Open Information / Information ouverte",
        }
        for id, res in data.items():
            status = res['status'] if \
                res['status'] != -1 else 'timeout / temps libre'
            portal_type = portal_type_dict.get(res['portal_type'], None)
            line = [res['url_en'], res['url_fr'],
                    portal_type, res['record_name_en'], res['record_name_fr'],
                    res['org_name_en'], res['org_name_fr'], res['name_en'],
                    res['name_fr'],  res['link'], status]
            out.writerow(line)
            count += 1
            if status == 'timeout / temps libre':
                count2 += 1
        outf.close()
        print(self.env.info())
        print(self.env.stat())
        print('total {0} dumped, timeout_count {1}'.format(count, count2))


def main():
    parser = argparse.ArgumentParser(
        description='''Search portal records broken resource link''')
    parser.add_argument("--file", dest="file", required=True,
                        help='''site gz file contains links. download from
                                http://open.canada.ca/static/od-do-canada.jl.gz.''')
    parser.add_argument("--quick", dest="quick", action='store_true',
                        help="skip testing recent failed links", default=False)
    parser.add_argument("--dump", dest="dump", help="dump to csv file")

    options = parser.parse_args()

    site = Records(options.file, options.quick)
    if options.dump:
        site.dumpBrokenLink(options.dump)
        return
    site.get_resources()


if __name__ == '__main__':
    main()
    sys.exit(0)
