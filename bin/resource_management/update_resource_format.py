#!/usr/bin/env python3
"""
Updates Resources based on incorrect_file_types_report.csv
Updates Content-type.
'source.action.resource_patch(id=resource_id,format=new_format)'

Input:
argv[1]: site URL
argv[2]: API Key
argv[3]: CSV Report ('incorrect_file_types_report.csv')

"""
import sys
import csv
import ckanapi

source = ckanapi.RemoteCKAN(sys.argv[1], apikey=sys.argv[2])
file_report = sys.argv[3]
with open(file_report) as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        uuid = row["uuid"]
        resource_id = row["resource_id"]
        new_format = unicode(row["found_file_type"].upper())
        old_format = row["metadata_file_type"]
        source.action.resource_patch(id=resource_id, format=new_format)
print("done")
