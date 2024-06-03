#!/usr/bin/env python3

import unicodecsv
import sys
from decimal import Decimal

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=in_csv.fieldnames, encoding='utf-8')
out_csv.writeheader()

try:
    for line in in_csv:
        line['service_std_target'] = "%0.2f" % (Decimal(line['service_std_target']) / 100)
        out_csv.writerow(line)

except KeyError:
    if 'warehouse' in sys.argv:
        sys.exit(85)
    else:
        raise
