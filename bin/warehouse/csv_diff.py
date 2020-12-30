#!/usr/bin/env python3
import json
import hashlib
import requests
import sys
import csv
import os
import io
from sys import stderr, stdout, argv
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def get_file_keys(csv_file, primary_keys):
    pk_list = {}
    with open(csv_file) as f:
        hashcsv = csv.DictReader(codecs.EncodedFile(f, 'utf-8', 'utf-8-sig'), delimiter=",")
        for row in hashcsv:
            primary_fields = [str(row[t]) for t in primary_keys]
            uid = '-'.join(primary_fields)
            pk_list[uid]=''
    f.close()
    return pk_list

def find_removed_and_created_keys(prev, curr):
    """

    :param prev: Older CSV
    :param curr: Newer CSV
    :return: The keys that were removed/added between the 2 CSVs, and the keys which MAY be modified
    """
    removed_keys = {}
    added_keys = {}
    mod_keys = {}

    for key in prev:
        if not key in curr:
            removed_keys[key] = ''
    for key in curr:
        if not key in prev:
            added_keys[key]=''
        else:
            mod_keys[key]=''

    return removed_keys, added_keys, mod_keys

def get_mod_keys(prev, curr, modkeys, primary_keys):
    """
    Get modified keys
    :param prev: The old CSV used for comparison
    :param curr: The newer CSV for comparison
    :param modkeys: The keys which may indicate modification in row
    :param primary_keys: Primary keys of PD type
    :return: The keys of rows which are modified between the old and new CSVs
    """
    res = {}
    with open(curr) as cf:
        currcsv = csv.DictReader(codecs.EncodedFile(cf, 'utf-8', 'utf-8-sig'), delimiter=",")
        for row in currcsv:
            primary_fields = [str(row[t]) for t in primary_keys]
            uid = '-'.join(primary_fields)
            if uid in modkeys:
                modkeys[uid]=row
    cf.close()
    with open(prev) as pf:
        prevcsv = csv.DictReader(codecs.EncodedFile(pf, 'utf-8', 'utf-8-sig'), delimiter=",")
        for row in prevcsv:
            primary_fields = [str(row[t]) for t in primary_keys]
            uid = '-'.join(primary_fields)
            if uid in modkeys:
                for field in row:
                    if row[field] != modkeys[uid][field]:
                        res[uid]=''
                        break
    pf.close()
    return res

def write_warehouse(out, csvfile, primary_keys, write_keys, writehead, fields, log_activity, date):
    """
    Write to warehouse CSV file in such a way that does not load entire CSV files to memory.
    :param out: warehouse file to write to
    :param csvfile: the CSV file used for reading/writing data to warehouse
    :param primary_keys: primary keys of PD type
    :param write_keys: the keys to be written (added keys, removed keys, modified keys)
    :param writehead: boolean to either write or ignore header
    :param fields: fields to be written to warehouse
    :param log_activity: C = created, D = deleted, M = modified
    :param date: date of comparison
    :return: None
    """
    with open(out, 'a') as f:
        warehouse = csv.DictWriter(f, fieldnames=fields, delimiter=',', restval='')
        if not exists_flag:
            warehouse.writeheader()
        with open(csvfile) as cf:
            hashcsv = csv.DictReader(codecs.EncodedFile(cf, 'utf-8', 'utf-8-sig'), delimiter=",")
            for row in hashcsv:
                primary_fields = [str(row[t]) for t in primary_keys]
                uid = '-'.join(primary_fields)
                if uid in write_keys:
                    res = row
                    res["log_date"] = date
                    res["log_activity"] = log_activity
                    l = list(res.keys())
                    for g in l:
                        if g not in fields:
                            del res[g]
                    warehouse.writerow(res)
        cf.close()
    f.close()

prev_csv, current_csv, endpoint, datestamp, outfile = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
"""
prev_csv = Older CSV being compared
current_csv = newer CSV being compared
endpoint = http address of fields and primary keys of current PD type
datestamp = current date of comparison
outfile = warehouse file for output
"""

field_info = requests.get(endpoint, timeout=100, verify=False).json()

# Grab the primary key fields from the datatype reference endpoint
if 'nil' in current_csv:
    pk_fields = [f['primary_key'] for f in field_info['resources'] if 'nil' in f['resource_name']]
    fields = [f['fields'] for f in field_info['resources'] if 'nil' in f['resource_name']]
else:
    pk_fields = [f['primary_key'] for f in field_info['resources'] if 'nil' not in f['resource_name']]
    fields = [f['fields'] for f in field_info['resources'] if 'nil' not in f['resource_name']]

pk_fields.append('owner_org')

#Get Primary Keys for all rows in prev and curr CSV
old_csv_keys = get_file_keys(prev_csv, pk_fields)
new_csv_keys = get_file_keys(current_csv, pk_fields)

#Compare keys to find Removed and Created Primary Keys and Candidate Mod keys
removed_keys, added_keys, mod_keys = find_removed_and_created_keys(old_csv_keys, new_csv_keys)

#Compare rows of mod_keys to confirm that rows were modified
mod_keys = get_mod_keys(prev_csv, current_csv, mod_keys, pk_fields)

if len(added_keys)==0 and len(removed_keys)==0 and len(mod_keys)==0:
    print("No changes detected between files")
else:
    print("No changes detected between files")
    exists_flag = os.path.isfile(outfile)
    #write created keys to warehouse file
    write_warehouse(outfile, current_csv, pk_fields, added_keys, exists_flag, fieldnames, "C", datestamp)
    exists_flag = True
    #write modified keys to warehouse file
    write_warehouse(outfile, current_csv, pk_fields, mod_keys, exists_flag, fieldnames, "M", datestamp)
    #write deleted keys to warehouse file
    write_warehouse(outfile, prev_csv, pk_fields, removed_keys, exists_flag, fieldnames, "D", datestamp)

