import sys
import csv
import ckanapi
"""
Updates Resources based on incorrect_file_types_report.csv
Updates Content-type and content-length (if applicable).
'source.action.resource_patch(id=resource_id,format=new_format)'

Input:
argv[1]: site URL
argv[2]: API Key
argv[3]: CSV Report ('incorrect_file_types_report.csv')

"""

source = ckanapi.RemoteCKAN(sys.argv[1],apikey=sys.argv[2])
file_report = sys.argv[3]
file = open(file_report, "r")
reader = csv.reader(file)
# skip head
next(reader)
for line in reader:
    uuid = line[4]
    resource_id = line[5]
    new_format = unicode(line[6].upper())
    old_format = line[7]
    print(uuid)
    source.action.resource_patch(id=resource_id,format=new_format)
file.close()
print("done")

