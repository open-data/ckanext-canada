#!/usr/bin/env python3

import csv
import sys

REMOVE_COLUMNS = [
    'record_created',
    'record_modified',
    'user_modified',
]

BOM = "\N{bom}"


def main():
    bom = sys.stdin.read(1)  # first code point
    if not bom:
        # empty file -> empty file
        return
    assert bom == BOM
    sys.stdout.write(BOM)

    reader = csv.DictReader(sys.stdin)
    outnames = ['owner_org'] + [f for f in reader.fieldnames
        if f not in REMOVE_COLUMNS and f != 'owner_org'] \
               + ['performance'] + ['target_met']
    writer = csv.DictWriter(sys.stdout, outnames)
    writer.writeheader()
    for row in reader:
        for rem in REMOVE_COLUMNS:
            del row[rem]

        num = int(row['volume_meeting_target']) if row['volume_meeting_target'] else 0
        den = int(row['total_volume']) if row['total_volume'] else 0

        # performance = volume_meeting_target / total_volume
        if num <= 0 or den <=0:
            row['performance'] = None
        else:
            row['performance'] = num / den

        # negative performance is not possible
        if row['performance'] and row['performance'] < 0:
            row['performance'] = 0

        # calculate target_met
        if row['target']:
            target = float(row['target'])

            # if no total_volume then target_met is not possible
            if den <= 0:
                row['target_met'] = 'NA'

            # if performance >= target then target is met
            elif row['performance'] >= target:
                row['target_met'] = 'Y'

            # otherwise target_met is not met
            else:
                row['target_met'] = 'N'
        else:
            row['target_met'] = None

        writer.writerow(row)

main()
