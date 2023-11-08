#!/usr/bin/env python
"""
This is an "update" script not a migrate script because it only
outputs records to be updated in-place, not a complete migrated
copy of the data, unless "warehouse" parameter is given
"""

import unicodecsv
import sys
import codecs

assert sys.stdin.read(3) == codecs.BOM_UTF8
sys.stdout.write(codecs.BOM_UTF8)

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
if not in_csv.fieldnames and 'warehouse' in sys.argv:
    sys.exit(85)
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=in_csv.fieldnames, encoding='utf-8')
out_csv.writeheader()

try:
    for line in in_csv:
        val = line['subjects'].split(',')
        if 'AP' not in val and 'warehouse' not in sys.argv:
            continue
        line['subjects'] = u','.join(
            'IP' if v == 'AP' else v for v in val)
        out_csv.writerow(line)

except KeyError:
    if 'warehouse' in sys.argv:
        sys.exit(85)
    else:
        raise
