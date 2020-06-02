import json
import hashlib
import requests
import sys
import csv
from sys import stderr, stdout, argv


def get_row_tuple(row):
    org_tuple = (row['owner_org'], row['owner_org_title'])
    #del row['owner_org']
    del row['owner_org_title']
    pk_tuple = tuple([row[key] for key in pk_fields[0]])
    h = hashlib.md5(repr(list(row.values())).encode('utf8')).digest()
    row_tuple = (pk_tuple, org_tuple, h)
    return row_tuple


def collect_existing_rows(prev_csv):
    '''
    return a set of hashes for rows in previous_dir/filtered/csv_name,
    excluding the organization fields to avoid counting org changes
    as row changes
    '''
    existing = set()
    with open(prev_csv) as f:
        hashcsv = csv.DictReader(f)
        for row in hashcsv:
            row_tuple = get_row_tuple(row)
            existing.add(row_tuple)
    return existing


def compare(current_csv, existing_rows):
    '''
    Check if a record in current_csv is also in prev_csv. If it isn't, append it to altered records list. If it is, then remove it from existing_rows.
    Returns three lists:
        created_rows contains records that were created since prev_csv
        modified_rows contains records that were modified since prev_csv
        deleted_rows contains hashes of records that were deleted since prev_csv
    '''
    created_rows = []
    modified_rows = []
    deleted_rows = existing_rows
    with open(current_csv) as f:
        hashcsv = csv.DictReader(f)
        for row in hashcsv:
            row_tuple = get_row_tuple(row)
            for t in existing_rows:
                if row_tuple[2] == t[2]:
                    deleted_rows.remove(t)
                    break
                elif row_tuple[0] == t[0] and row_tuple[1] == t[1]:
                    modified_rows.append(row)

                    break
            else:
                created_rows.append(row)

    return created_rows, modified_rows, deleted_rows


def add_metadata_fields(created_rows, modified_rows, deleted_rows, prev_csv, datestamp):
    results = []
    for cr in created_rows:
        cr['log_date'] = datestamp
        cr['log_activity'] = 'C'
        results.append(cr)

    for mr in modified_rows:
        mr['log_date'] = datestamp
        mr['log_activity'] = 'M'
        results.append(mr)

    with open(prev_csv) as f:
        pcsv = csv.DictReader(f)
        for t in deleted_rows:
            for row in pcsv:
                row_tuple = get_row_tuple(row)
                if t[0] == row_tuple[0] and t[1] == row_tuple[1]:
                    row['log_date'] = datestamp
                    row['log_activity'] = 'D'
                    results.append(row)
                    break
    return results


def get_fieldnames(fields):
    fieldnames = ",".join([f['id'] for f in fields])+",owner_org,log_date,log_activity"
    return fieldnames


prev_csv, current_csv, endpoint, datestamp, outfile = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
field_info = requests.get(endpoint).json()

# Grab the primary key fields from the datatype reference endpoint
if 'nil' in current_csv:
    pk_fields = [f['primary_key'] for f in field_info['resources'] if 'nil' in f['resource_name']]
    fields = [f['fields'] for f in field_info['resources'] if 'nil' in f['resource_name']]
else:
    pk_fields = [f['primary_key'] for f in field_info['resources'] if 'nil' not in f['resource_name']]
    fields = [f['fields'] for f in field_info['resources'] if 'nil' not in f['resource_name']]

fieldnames = get_fieldnames(fields[0]).split(",")
print(fieldnames)
existing_rows = collect_existing_rows(prev_csv)
print("Comparing...")
created_rows, modified_rows, deleted_rows = compare(current_csv, existing_rows)
results = add_metadata_fields(created_rows, modified_rows, deleted_rows, prev_csv, datestamp)

print("writing")
if results:
    with open(outfile, 'a') as f:
        warehouse = csv.DictWriter(f, fieldnames=fieldnames, delimiter=',', restval='')
        warehouse.writeheader()
        for result_row in results:
            for key in result_row.keys():
                if key not in fieldnames:
                    result_row.pop(key)
                if key == 'record_created':
                    result_row['record_created'] = (result_row['record_created'].split('T')[0]).replace('/','-')
                if key == 'record_modified':
                    result_row['record_modified'] = (result_row['record_modified'].split('T')[0]).replace('/','-')
                print(result_row)
            warehouse.writerow(result_row)

else:
    print("No changes detected between files")
