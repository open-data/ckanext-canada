#!/usr/bin/env python

"""
Script that takes csv on stdin with an eligible_for_release column
and outputs the header row and all rows eligible_for_release
"""

import csv
import sys

FILTER_COLUMN = "eligible_for_release"
REMOVE_COLUMN = "user_votes"


def main():
    reader = csv.DictReader(sys.stdin)
    outnames = [f for f in reader.fieldnames if f != REMOVE_COLUMN]
    writer = csv.DictWriter(sys.stdout, outnames)
    writer.writeheader()
    for row in reader:
        try:
            if asbool(row[FILTER_COLUMN]):
                row[FILTER_COLUMN] = 'Y'
                if REMOVE_COLUMN in row:
                    del row[REMOVE_COLUMN]
                writer.writerow(row)
        except ValueError:
            pass


# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php


truthy = frozenset(['true', 'yes', 'on', 'y', 't', '1'])
falsy = frozenset(['false', 'no', 'off', 'n', 'f', '0'])


def asbool(obj):
    if isinstance(obj, str):
        obj = obj.strip().lower()
        if obj in truthy:
            return True
        elif obj in falsy:
            return False
        else:
            raise ValueError("String is not true/false: %r" % obj)
    return bool(obj)


main()
