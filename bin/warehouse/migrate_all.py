#!/usr/bin/env python3
"""
This script takes proactive disclosure data in the form of a csv file and runs it against the corresponding migration scripts
"""

import sys
import codecs
import glob
import io
import os, errno
import subprocess
import shutil


def run_scripts(infile, outfile, matching_files):
    # Remove any dead procedures from previous calls to this method
    if proc_array:
        proc_array[:] = []

    # Covers the case where there is only one migration script for the given type
    if len(matching_files) == 1:
        proc_array.append(subprocess.Popen(["python", matching_files[0], 'warehouse'], stdin=subprocess.PIPE, stdout=outfile))

    else:
        for matching_file in matching_files:
            print("Starting process: {0} with {1}".format(matching_files.index(matching_file), matching_file))
            if len(proc_array) == 0:
                proc_array.append(subprocess.Popen(['python', matching_file, 'warehouse'], stdin=subprocess.PIPE, stdout=subprocess.PIPE))
            elif matching_file == matching_files[-1]:
                proc_array.append(subprocess.Popen(['python', matching_file, 'warehouse'], stdin=proc_array[-1].stdout, stdout=outfile))
            else:
                proc_array.append(subprocess.Popen(['python', matching_file, 'warehouse'], stdin=proc_array[-1].stdout, stdout=subprocess.PIPE))

    # Check if the input csv has a byte order marks
    if infile.read(3) != codecs.BOM_UTF8:
        proc_array[0].stdin.write(codecs.BOM_UTF8)

    infile.seek(0)

    try:
    # writing, flushing, whatever goes here
        for chunk in iter(lambda: infile.read(1000), ''):
            proc_array[0].stdin.write(chunk)
        proc_array[0].stdin.close()
    except IOError as e:
        # skip if it's just a SIGPIPE signal exception
        if e.errno != errno.EPIPE:
            raise 

    while proc_array[0].poll() is None:
        pass


inpath = sys.argv[1]
outpath = sys.argv[2]
infile = io.open(inpath, mode='rb')
outfile = io.open(outpath, mode='wb')
base = os.path.basename(inpath)
pd_type = os.path.splitext(base)[0]
proc_array = []

# Check if the input csv file is a *-nil data type, and retrieve only the nil migration scripts
if "nil" not in pd_type:
    search_pd = '*_{0}_*'.format(pd_type)
    matching_files = sorted([mf for mf in glob.glob('../migrate/'+search_pd) if "nil" not in mf])

else:
    pd_type = pd_type.replace("-", "_")
    search_pd = '*_{0}_*'.format(pd_type)
    matching_files = sorted(glob.glob('../migrate/' + search_pd))

while matching_files:
    try:
        run_scripts(infile, outfile, matching_files)
        break

    except IOError:
        if proc_array[0].poll() != 85:
            raise
        infile.seek(0)
        outfile.seek(0)
        matching_files = matching_files[1:]
# if there are no migration scripts to run, write the csv file to output file
else:
    shutil.copyfile(inpath, outpath)

infile.close()
outfile.close()
