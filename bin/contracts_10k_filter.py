#!/usr/bin/env python

"""
Script that takes contracts csv on stdin with a
"Total Contract Value / Valeur totale du contrat" column
outputs the header row and all rows with total value > 10k
"""

import csv
import sys

VALUE_COLUMN = "Total Contract Value / Valeur totale du contrat"
MINIMUM_CONTRACT_VALUE = 10000

def main():
    reader = csv.DictReader(sys.stdin)
    writer = csv.DictWriter(sys.stdout, reader.fieldnames)
    writer.writeheader()
    for row in reader:
        try:
            v = float(row[VALUE_COLUMN])
        except ValueError:
            continue
        if v < MINIMUM_CONTRACT_VALUE:
            continue
        writer.writerow(row)

main()
