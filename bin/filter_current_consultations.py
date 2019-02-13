#!/usr/bin/env python

"""
Script that takes csv on stdin with Year, Month as the first two columns
and outputs the header row and all rows within the past two years on stdout
"""

from datetime import datetime, timedelta
import csv
import sys

def main():
    current = datetime.today() - timedelta(365 * 2)

    reader = csv.DictReader(sys.stdin)
    writer = csv.DictWriter(sys.stdout, reader.fieldnames)
    writer.writeheader()
    for row in reader:
        if datetime.strptime(row['end_date'], '%Y-%m-%d') > current:
            writer.writerow(row)

main()
