#!/usr/bin/env python3

"""
Script that takes csv on stdin and writes an xlsx file on stdout
"""

import csv
import codecs
import sys
import openpyxl

def main():
    reader = csv.reader(sys.stdin)
    book = openpyxl.Workbook(write_only=True)
    sheet = book.create_sheet()

    firstrow = next(reader)
    firstrow[0] = firstrow[0].lstrip(codecs.BOM_UTF8)
    sheet.append(firstrow)

    for row in reader:
        sheet.append(row)

    book.save(sys.stdout)

main()
