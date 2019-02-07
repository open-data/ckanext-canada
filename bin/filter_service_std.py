#!/usr/bin/env python

import csv
import sys
import codecs

REMOVE_COLUMNS = [
    'record_created',
    'record_modified',
    'user_modified',
]

def main():
    bom = sys.stdin.read(3)
    assert bom == codecs.BOM_UTF8
    sys.stdout.write(codecs.BOM_UTF8)

    reader = csv.DictReader(sys.stdin)
    outnames = ['owner_org'] + [f for f in reader.fieldnames
        if f not in REMOVE_COLUMNS and f != 'owner_org'
        ] + ['performance']
    writer = csv.DictWriter(sys.stdout, outnames)
    writer.writeheader()
    for row in reader:
        for rem in REMOVE_COLUMNS:
            del row[rem]
        num = 0
        den = 0
        try:
            num, den = num + int(row['q1_performance_result']), den + int(row['q1_business_volume'])
        except ValueError:
            pass
        try:
            num, den = num + int(row['q2_performance_result']), den + int(row['q2_business_volume'])
        except ValueError:
            pass
        try:
            num, den = num + int(row['q3_performance_result']), den + int(row['q3_business_volume'])
        except ValueError:
            pass
        try:
            num, den = num + int(row['q4_performance_result']), den + int(row['q4_business_volume'])
        except ValueError:
            pass
        if not den:
            row['performance'] = 'ND'
        else:
            row['performance'] = '%0.5f' % (float(num) / den)
        writer.writerow(row)

main()
