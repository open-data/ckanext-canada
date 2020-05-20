import sys
import grequests
import fileinput
from datetime import datetime
import json
import csv

"""
Fetches URL's from metadata and tests URL status in parallel using grequests library.
Outputs status to 'url_database.csv'

Arguments:
fileinput - metadata file to be read ('od-do-canada.jsonl')
batch_size - maximum number of URL's to test in parallel
"""

batch_size = int(sys.argv[2])

i = 1
prev_i = 1
urls = []
batch_urls = []
responses = []
date = []


print("Starting...")
print("Reading and testing URL's")

for dataset in fileinput.input():
    line = json.loads(dataset)
    resources = line["resources"]
    for l in range(len(resources)):
        url = resources[l]["url"]
        if url in urls:
            continue;
        else:
            urls.append(url)
            now = datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M")
            date.append(dt_string)
            batch_urls.append(url)
            if len(batch_urls)==batch_size:
                sys.stderr.write("\r")
                sys.stderr.write("Testing Datasets {0} - {1}".format(prev_i, i))
                prev_i=i
                rs = (grequests.get(u) for u in batch_urls)
                responses.append(grequests.map(rs))
                batch_urls = []
    i+=1

#Check last urls not covered in loop
sys.stderr.write("\r")
sys.stderr.write("Testing Datasets {0} - {1}".format(prev_i, i))
rs = (grequests.get(u) for u in batch_urls)
responses.append(grequests.map(rs))
dataset_urls=[]

print("Fetching content data...")

responses=sum(responses,[])
content_lengths=[]
content_types=[]


for z in range(len(responses)):
    r=responses[z]
    if r is None:
        content_lengths.append('not-found')
        content_types.append('not-found')
        responses[z] = 'not-found'
    else:
        cl = r.headers.get("Content-Length")
        ct = r.headers.get("Content-Type")
        if cl is None:
            cd = 'not-found'
        if ct is None:
            ct='not-found'
        content_lengths.append(cl)
        content_types.append(ct)

print("Exporting to csv...")
rows = zip(urls,date,responses,content_types,content_lengths)

with open('url_database.csv', "w") as f:
    writer = csv.writer(f)
    writer.writerow(("url", "date","response","content-type","content-length"))
    for row in rows:
        writer.writerow(row)
f.close()
print("Done.")




