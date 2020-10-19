#!/usr/bin/env python3
"""
Fetches URL's from metadata and tests URL status in parallel using
grequests library.
Outputs status to 'url_database.csv'

Arguments:
fileinput - metadata file to be read ('od-do-canada.jsonl') or retest 'N/A' responses from previous url_database.csv
batch_size - INT maximum number of URL's to test in parallel
filename - name of file to export
"""
import sys
import grequests
import requests
import requests_ftp
import fileinput
from datetime import datetime
import json
import csv
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# use a generic user agent to detect services that render information pages instead of the actual data when a web browser user visits
GENERIC_WEB_CLIENT_AGENT = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"}

def create_database(filename):
    with open(filename, "w") as f:
        writer = csv.writer(f)
        writer.writerow(("url", "date", "response",
                         "content-type", "content-length"))
    f.close()

def write_to_database(filename, rows):
    with open(filename, "a") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    f.close()

def check_for_connection():
    url = "https://www.google.ca"
    timeout = 5
    connected = False
    while(connected==False):
        try:
            request = requests.get(url, timeout=timeout)
            connected=True
        except (requests.ConnectionError, requests.Timeout) as exception:
            print("No internet connection.")

def get_batch_response(batch_urls, i, prev_i):
    sys.stderr.write("\r")
    sys.stderr.write("Testing Datasets {0} - {1}".format(prev_i, i))
    rs = (grequests.head(u, timeout=60, headers=GENERIC_WEB_CLIENT_AGENT, verify=False, allow_redirects=True, stream=False) for u in
          batch_urls)
    batch_response = grequests.map(rs)
    for j, r in enumerate(batch_response):
        if not r is None:
            r.close()
        else:
            batch_response[j] = "N/A"
    return batch_response

def get_batch_response_ftp(batch_urls):
    ftp_responses = []
    ftp_dates = []
    requests_ftp.monkeypatch_session()
    for i, url in enumerate(batch_urls):
        sys.stderr.write("\r")
        sys.stderr.write("Testing FTP {0} of {1}".format(i, len(batch_urls)))
        s = requests.Session()
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        ftp_dates.append(dt_string.encode('utf-8'))
        try:
            resp = s.head(url, timeout=120, headers=GENERIC_WEB_CLIENT_AGENT, verify=False, allow_redirects=True, stream=False)

            if not resp is None:
                s.close()
            else:
                resp = "N/A"
            ftp_responses.append(resp)
        except requests.exceptions.RequestException as e:
            ftp_responses.append("N/A")
            continue
        except UnicodeEncodeError as e:
            ftp_responses.append("N/A")
            continue
    return ftp_responses, ftp_dates

def get_batch_content(batch_response):
    content_lengths = []
    content_types = []
    for r in batch_response:
        if "N/A" in r:
            content_lengths.append('N/A')
            content_types.append('N/A')
        else:
            cl = r.headers.get("Content-Length")
            ct = r.headers.get("Content-Type")
            if cl is None:
                cl = 'N/A'
            if ct is None:
                ct = 'N/A'
            content_lengths.append(cl.encode('utf-8'))
            content_types.append(ct.encode('utf-8'))
    return content_lengths, content_types

def main(import_file, batch_size, filename):
    # set local vars
    prev_i = 1
    all_urls = set()
    ftp_urls = []
    # batch lists
    batch_urls = []
    batch_dates = []
    # create url_database file
    create_database(filename)
    # Open JSONL and retrieve urls
    for i, dataset in enumerate(open(import_file), 1):
        line = json.loads(dataset, "utf-8")
        resources = line["resources"]
        for l in range(len(resources)):
            # append urls to temp list
            url = resources[l]["url"]
            url = str(url.encode('utf-8'))
            if url in all_urls:
                continue
            elif 'ftp://' in url:
                all_urls.add(url)
                ftp_urls.append(url)
            else:
                all_urls.add(url)
                batch_urls.append(url)
                now = datetime.now()
                dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
                batch_dates.append(dt_string.encode('utf-8'))
            # when len(list) == batch_size
            if len(batch_urls) == batch_size:
                check_for_connection()
                # get batch_responses as list
                batch_response = get_batch_response(batch_urls, i, prev_i)
                prev_i = i
                # get content-length and content-type from responses list
                batch_cl , batch_ct = get_batch_content(batch_response)
                # zip urls, dates, responses, content-type, content-length
                rows = zip(batch_urls, batch_dates, batch_response, batch_ct, batch_cl)
                # write rows to csv
                write_to_database(filename, rows)
                # clear lists and repeat
                batch_urls = []
                batch_dates = []

    # Get response info for last URLS not included in final batch
    check_for_connection()
    batch_response = get_batch_response(batch_urls, i, prev_i)
    batch_cl, batch_ct = get_batch_content(batch_response)
    rows = zip(batch_urls, batch_dates, batch_response, batch_ct, batch_cl)
    write_to_database(filename, rows)
    batch_urls = []
    batch_dates = []

    # get response info for FTP links
    check_for_connection()
    ftp_batch_response, ftp_dates  = get_batch_response_ftp(ftp_urls)
    batch_cl, batch_ct = get_batch_content(ftp_batch_response)
    rows = zip(ftp_urls, ftp_dates, ftp_batch_response, batch_ct, batch_cl)
    write_to_database(filename, rows)

def retest(import_file, batch_size, filename):
    create_database(filename)
    with open(import_file, "r") as csvfile:
        reader = csv.reader(csvfile)
        next(reader)
        prev_i = 1
        ftp_urls = []
        # batch lists
        batch_urls = []
        batch_dates = []
        for i, row in enumerate(reader):
            url = row[0]
            date = row[1]
            response = row[2]
            content_length = row[3]
            content_type = row[4]
            if 'N/A' in response:
                if 'ftp://' in url:
                    ftp_urls.append(url)
                else:
                    batch_urls.append(url)
                    now = datetime.now()
                    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
                    batch_dates.append(dt_string.encode('utf-8'))
                    # when len(list) == batch_size
                if len(batch_urls) == batch_size:
                    check_for_connection()
                    # get batch_responses as list
                    batch_response = get_batch_response(batch_urls, i, prev_i)
                    prev_i = i
                    # get content-length and content-type from responses list
                    batch_cl, batch_ct = get_batch_content(batch_response)
                    # zip urls, dates, responses, content-type, content-length
                    rows = zip(batch_urls, batch_dates, batch_response, batch_ct, batch_cl)
                    # write rows to csv
                    write_to_database(filename, rows)
                    # clear lists and repeat
                    batch_urls = []
                    batch_dates = []
            else:
                write_to_database(filename,[row])
    csvfile.close()
    # Get response info for last URLS not included in final batch
    check_for_connection()
    batch_response = get_batch_response(batch_urls, i, prev_i)
    batch_cl, batch_ct = get_batch_content(batch_response)
    rows = zip(batch_urls, batch_dates, batch_response, batch_ct, batch_cl)
    write_to_database(filename, rows)
    batch_urls = []
    batch_dates = []

    # get response info for FTP links
    check_for_connection()
    ftp_batch_response, ftp_dates = get_batch_response_ftp(ftp_urls)
    batch_cl, batch_ct = get_batch_content(ftp_batch_response)
    rows = zip(ftp_urls, ftp_dates, ftp_batch_response, batch_ct, batch_cl)
    write_to_database(filename, rows)

if __name__ == '__main__':
    import_file = sys.argv[1]
    batch_size = int(sys.argv[2])
    filename = sys.argv[3]
    print(import_file, batch_size, filename)
    if 'jsonl' in import_file or '.jl' in import_file:
        main(import_file, batch_size, filename)
    elif '.csv' in import_file:
        retest(import_file, batch_size, filename)


