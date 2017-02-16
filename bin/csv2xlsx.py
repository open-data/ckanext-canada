#!/usr/bin/env python

"""
Script that takes csv on stdin and writes an xlsx file on stdout
"""

import csv
import codecs
import sys
import openpyxl

def peekBOM(f):
    first3bytes = f.read(3)
    if first3bytes == codecs.BOM_UTF8:
        f.seek(3)
    else:
        f.seek(0)
    return f

def main():
    reader = csv.reader(peekBOM(sys.stdin))
    book = openpyxl.Workbook(write_only=True)
    sheet = book.create_sheet()

    for row in reader:
        sheet.append(row)

    book.save(sys.stdout)

main()
