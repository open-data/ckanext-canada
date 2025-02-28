#!/usr/bin/env python3
"""
Fetches URL's from metadata and tests URL status in parallel using
grequests library.
Outputs status to 'url_database.csv'

Arguments:
fileinput - metadata file to be read ('od-do-canada.jsonl.gz')
batch_size - maximum number of URL's to test in parallel
"""
import sys
import grequests
import requests
import requests_ftp
from datetime import datetime
import json
import csv
import gzip
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

file = sys.argv[1]
batch_size = int(sys.argv[2])

print(file, batch_size)

prev_i = 1
urls = set()
batch_urls = []
url_match = []
responses = []
date = []
ftp_urls = []
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"}


def check_for_connection():
    url = "https://www.google.ca"
    timeout = 5
    connected = False
    while connected is False:
        try:
            requests.get(url, timeout=timeout)
            connected = True
        except (requests.ConnectionError, requests.Timeout):
            print("No internet connection.")


print("Starting...")
print("Reading and testing URL's")

for i, dataset in enumerate(gzip.open(file), 1):
    line = json.loads(dataset)
    resources = line["resources"]
    for rline in range(len(resources)):
        url = resources[rline]["url"].encode('utf-8')
        if url in urls:
            continue
        elif 'ftp://' in url:
            ftp_urls.append(url)
        else:
            urls.add(url)
            now = datetime.now()
            dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
            date.append(dt_string.encode('utf-8'))
            batch_urls.append(url)

            if len(batch_urls) == batch_size:
                url_match.append(batch_urls)
                sys.stderr.write("\r")
                sys.stderr.write("Testing Datasets {0} - {1}"
                                 .format(prev_i, i))
                prev_i = i
                rs = (grequests.head(u, timeout=10,
                                     headers=headers,
                                     verify=False, allow_redirects=True,
                                     stream=False) for u in batch_urls)
                batch_response = grequests.map(rs)
                responses.append(batch_response)
                for r in batch_response:
                    if r is not None:
                        r.close()
                batch_urls = []
                check_for_connection()

# Check last urls not covered in loop
url_match.append(batch_urls)
sys.stderr.write("\r")
sys.stderr.write("Testing Datasets {0} - {1}".format(prev_i, i))
rs = (grequests.head(u, timeout=10, headers=headers,
                     verify=False, allow_redirects=True,
                     stream=False) for u in batch_urls)
batch_response = grequests.map(rs)
responses.append(batch_response)
for r in batch_response:
    if r is not None:
        r.close()

# Testing FTP urls
ftp_batch = []
ftp_response = []

requests_ftp.monkeypatch_session()

for i, url in enumerate(ftp_urls):
    sys.stderr.write("\r")
    sys.stderr.write("Testing FTP {0} of {1}".format(i, len(ftp_urls)))
    s = requests.Session()
    try:
        resp = s.head(url, timeout=10, headers=headers, verify=False,
                      allow_redirects=True, stream=False)
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        date.append(dt_string.encode('utf-8'))
        ftp_batch.append(url)
        ftp_response.append(resp)
        if resp is not None:
            s.close()
        if i % batch_size == 0:
            check_for_connection()
    except (requests.exceptions.RequestException, UnicodeEncodeError) as e:
        print(str(e))
        ftp_batch.append(url)
        ftp_response.append(None)
        continue

responses.append(ftp_response)
url_match.append(ftp_batch)

print("Fetching content data...")

responses = sum(responses, [])
url_match = sum(url_match, [])
content_lengths = []
content_types = []
for z, r in enumerate(responses):
    if r is None:
        content_lengths.append('N/A')
        content_types.append('N/A')
        responses[z] = 'N/A'
    else:
        cl = r.headers.get("Content-Length")
        ct = r.headers.get("Content-Type")
        if cl is None:
            cl = 'N/A'
        if ct is None:
            ct = 'N/A'
        content_lengths.append(cl.encode('utf-8'))
        content_types.append(ct.encode('utf-8'))

print("Exporting to csv...")
rows = zip(url_match, date, responses, content_types, content_lengths)

with open('url_database.csv', "w") as f:
    writer = csv.writer(f)
    writer.writerow(("url", "date", "response", "content-type",
                     "content-length"))
    for row in rows:
        writer.writerow(row)
f.close()
print("Done.")
