#!/usr/bin/env python

import sys
import json

import unicodecsv

try:
    infile = sys.argv[1]
    outfile = sys.argv[2]
    colnames = sys.argv[3]

except:
    sys.stderr.write('''Usage:
    jsonlerrors2csv input.jsonl output.csv 'col1,col2,...'

Reformat the error output from "recombinant load-csv" into a
csv file that includes error messages and may be used to correct
data or validation rules before attempting to re-import.

col1,col2,... can be obtained with "head -1 existing-pd.csv"
''')
    sys.exit(1)

out_csv = unicodecsv.DictWriter(
    open(outfile, 'wb'),
    fieldnames=['errors'] + colnames.split(','),
)
out_csv.writeheader()

inf = open(infile)
for line in inf:
    try:
        errors, owner_org, data = json.loads(line)
    except ValueError:
        sys.stderr.write('Ignoring line: ' + line)
        continue

    data['owner_org'] = owner_org
    data['errors'] = json.dumps(errors)
    try:
        out_csv.writerow(data)
    except ValueError:
        sys.stderr.write('Wrong columns: ' + line)
