#!/usr/bin/env python

"""
Script that takes csv on stdin and writes an xlsx file on stdout
"""

import csv
import sys
import openpyxl

def main():
    reader = csv.reader(sys.stdin)
    book = openpyxl.Workbook()
    sheet = book.active

    for row in reader:
        sheet.append(row)

    book.save(sys.stdout)

main()
