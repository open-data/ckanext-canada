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
import tempfile
from datetime import datetime
import argparse

parser = argparse.ArgumentParser(description="Run warehouse script. By default, it runs on the last 2 backups.")
parser.add_argument("fname", help="directory of archived backups")
parser.add_argument("-a", "--all", action='store_true', help="compare all backups.")
args = parser.parse_args()

tar_array = sorted(os.listdir(args.fname))
if args.all == False:
    tar_array = tar_array[-2:]

prev = ''
curr = ''

def get_base(tfile):
    base = os.path.basename(tfile)
    pd_name = os.path.splitext(os.path.splitext(base)[0])[0]
    return pd_name

def extract(tfile, dest):
    fpath = './' + dest
    tar = tarfile.open(args.fname + tfile)
    tar.extractall(path=fpath)
    tar.close()
    return fpath

def run_migrations(fpath, temp_dir):

    for csvfile in os.listdir(fpath):
        print("Migrating {0} from directory {1}".format(csvfile, fpath))
        proc = subprocess.Popen(['python', 'migrate_all.py', fpath+'/'+csvfile, temp_dir+'/'+fpath+'m_'+csvfile])
        if proc.wait():
            sys.exit(1)

def csv_diff(prev_csv, curr_csv, endpoint, outfile):
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d")

    print("Getting difference between {0} and {1}".format(prev_csv, curr_csv))
    proc = subprocess.Popen(['python', 'csv_diff.py', temp_dir+'/'+prev_csv, temp_dir+'/'+curr_csv, endpoint,
                             dt_string, outfile])
    if proc.wait():
            sys.exit(1)


if not os.path.exists('warehouse_reports'):
    os.mkdir('warehouse_reports')

while tar_array:
    with tempfile.TemporaryDirectory() as temp_dir:
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
        run_migrations(prev_path, temp_dir)
        run_migrations(curr_path, temp_dir)

        # Delete extracted directories
        shutil.rmtree(prev_path)
        shutil.rmtree(curr_path)

        # Match Migrated CSVs
        csv_array = sorted(os.listdir(temp_dir))
        prev_array = [a for a in csv_array if prev_base in a]
        curr_array = [a for a in csv_array if curr_base in a]

        for i in range(len(prev_array)):
            now = datetime.now()
            dt_string = now.strftime("%H:%M:%s")
            print(dt_string,'\n')
            pdtype = prev_array[i].split('_')[1].split('.')[0]
            schema = pdtype
            if 'nil' in pdtype or 'std' in pdtype:
                schema = schema.split('-')[0]
            csv_diff(prev_array[i], curr_array[i],
                'http://open.canada.ca/data/en/recombinant-schema/{0}.json'.format(schema),
                'warehouse_reports/{0}_warehouse.csv'.format(pdtype))


