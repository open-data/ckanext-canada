#!/usr/bin/env python3
"""
Updates Resources based on incorrect_file_size_report.csv
'source.action.resource_patch(id=resource_id,size=new_size)'

Input:
argv[1]: site URL
argv[2]: API Key
argv[3]: CSV Report ('incorrect_file_sizes_report.csv')

"""
import sys
import csv
import ckanapi
import ckan

source = ckanapi.RemoteCKAN(sys.argv[1],apikey=sys.argv[2])
file_report = sys.argv[3]
print("Updating resource file sizes")
with open(file_report) as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        uuid = row["uuid"]
        resource_id = row["resource_id"]
        new_size = unicode(row["found_file_size"])
        try:
            s = source.action.resource_show(id=resource_id)
            s = source.action.resource_patch(id=resource_id, size=new_size)
            print("Updated: ",[uuid, resource_id,s.get("size")])
        except ckan.logic.NotFound as e:
            print("{0} dataset not found".format(uuid))
print("done")
