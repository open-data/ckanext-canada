#!/usr/bin/env python

"""
Script that takes csv on stdin with an eligible_for_release column
and outputs the header row and all rows eligible_for_release
"""

import csv
import sys
from paste.deploy.converters import asbool

FILTER_COLUMN = "eligible_for_release"

def main():
    reader = csv.DictReader(sys.stdin)
    writer = csv.DictWriter(sys.stdout, reader.fieldnames)
    writer.writerow(dict(zip(reader.fieldnames, reader.fieldnames)))
    for row in reader:
        if asbool(row[FILTER_COLUMN]):
            writer.writerow(row)

main()
