#!/usr/bin/env python3

"""
Script that takes csv on stdin with an disclosure_group column
and outputs the header row and all rows with disclosure_group
!= "MPSES" (Minister/Parliamentary Secretaries/Exempt Staff)
"""

import csv
import sys

FILTER_COLUMN = "disclosure_group"

def main():
    reader = csv.DictReader(sys.stdin)
    writer = csv.DictWriter(sys.stdout, reader.fieldnames)
    writer.writerow(dict(zip(reader.fieldnames, reader.fieldnames)))
    for row in reader:
        try:
            if row[FILTER_COLUMN] != 'MPSES':
                writer.writerow(row)
        except ValueError:
            pass

main()
