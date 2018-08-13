#!/usr/bin/env python

"""
Script that takes csv on stdin with Year, Month as the first two columns
and outputs the header row and all rows within the past two years on stdout
"""

import datetime
import csv
import sys

WINDOW_YEARS = 2

def main():
    today = datetime.datetime.today()
    start_year_month = (today.year - WINDOW_YEARS, today.month)

    writer = csv.writer(sys.stdout)
    reader = csv.reader(sys.stdin)
    writer.writerow(next(reader))  # header
    for row in reader:
        try:
            if (int(row[0]), int(row[1])) >= start_year_month:
                writer.writerow(row)
        except ValueError:
            pass

main()
