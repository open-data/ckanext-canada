#!/usr/bin/env python3
"""
Creates Warehouse for all PD-Types found in archived backups.

Arguments:
fname - directory of archived backups
operation - '-d' to compare last 2 backups (default), '-a' to compare all backups.
"""
import tarfile
import sys
import os
import subprocess
import shutil
from datetime import datetime

fname = sys.argv[1]

if len(sys.argv) == 3:
    operation = sys.argv[2]
    if operation != '-a' and operation != '-d':
        sys.exit("Error: invalid operation value (sys.argv[2]), -d or -a expected")
else:
    operation = "-d"

tar_array = sorted(os.listdir(fname))
if operation == "-d":
    tar_array = tar_array[-2:]
print(tar_array)
prev = ''
curr = ''

def get_base(tfile):
    base = os.path.basename(tfile)
    pd_name = os.path.splitext(os.path.splitext(base)[0])[0]
    return pd_name

def extract(tfile, dest):
    fpath = './' + dest
    tar = tarfile.open(fname + tfile)
    tar.extractall(path=fpath)
    tar.close()
    return fpath

def run_migrations(fpath):
    if not os.path.exists('temp'):
        os.mkdir('temp')
    for csvfile in os.listdir(fpath):
        print("Migrating {0} from directory {1}".format(csvfile, fpath))
        proc = subprocess.Popen(['python', 'migrate_all.py', fpath+'/'+csvfile, 'temp/'+fpath+'m_'+csvfile])
        proc.wait()

def csv_diff(prev_csv, curr_csv, endpoint, outfile):
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d")

    print("Getting difference between {0} and {1}".format(prev_csv, curr_csv))
    proc = subprocess.Popen(['python', 'csv_diff.py', 'temp/'+prev_csv, 'temp/'+curr_csv, endpoint,
                             dt_string, outfile])
    proc.wait()


if not os.path.exists('warehouse_reports'):
    os.mkdir('warehouse_reports')

while tar_array:
    if tar_array == []:
        break
    if prev == '':
        prev = tar_array.pop(0)
        curr = tar_array.pop(0)
    else:
        prev = curr
        curr = tar_array.pop(0)

    prev_base = get_base(prev)
    curr_base = get_base(curr)

    # Extract zipped backups
    prev_path = extract(prev, prev_base)
    curr_path = extract(curr, curr_base)

    # Migrate all CSVs
    run_migrations(prev_path)
    run_migrations(curr_path)

    # Delete extracted directories
    shutil.rmtree(prev_path)
    shutil.rmtree(curr_path)

    # Match Migrated CSVs
    csv_array = sorted(os.listdir('temp'))
    prev_array = [a for a in csv_array if prev_base in a]
    curr_array = [a for a in csv_array if curr_base in a]

    for i in range(len(prev_array)):
        now = datetime.now()
        dt_string = now.strftime("%H:%M:%s")
        print(dt_string,'\n')
        pdtype = prev_array[i].split('_')[1].split('.')[0]
        schema = pdtype
        if 'nil' in pdtype:
            schema = schema.split('-')[0]

        csv_diff(prev_array[i], curr_array[i],
            'http://open.canada.ca/data/en/recombinant-schema/{0}.json'.format(schema),
            'warehouse_reports/{0}_warehouse_test.csv'.format(pdtype))

    shutil.rmtree('temp')
