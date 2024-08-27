#!/usr/bin/env python3

import csv
import sys

REMOVE_COLUMNS = [
    'record_created',
    'record_modified',
    'user_modified',
]

COLUMNS = [
    'fiscal_yr', 'service_id', 'service_name_en', 'service_name_fr',
    'service_standard_id', 'service_standard_en', 'service_standard_fr',
    'type', 'channel', 'channel_comments_en', 'channel_comments_fr',
    'target', 'volume_meeting_target', 'total_volume', 'performance',
    'comments_en', 'comments_fr', 'target_met',
    'standards_targets_uri_en', 'standards_targets_uri_fr',
    'performance_results_uri_en', 'performance_results_uri_fr',
    'owner_org', 'owner_org_title',
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
    writer = csv.DictWriter(sys.stdout, COLUMNS)
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
            row['performance'] = max( round(num / den, 4), 0)

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
