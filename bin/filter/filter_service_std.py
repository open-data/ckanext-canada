#!/usr/bin/env python3

import csv
import sys

from typing import Dict, Any


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


def test(record: Dict[str, Any]) -> Dict[str, Any]:
    return process_row(record)


def process_row(row: Dict[str, Any]) -> Dict[str, Any]:
    for rem in REMOVE_COLUMNS:
        if rem in row:
            del row[rem]

    num = int(row['volume_meeting_target']) if row['volume_meeting_target'] else 0
    den = int(row['total_volume']) if row['total_volume'] else 0

    # performance = volume_meeting_target / total_volume
    if den <= 0 or row['volume_meeting_target'] is None:
        # denominator is 0 so calculation is NaN, or
        # volume_meeting_target is empty,
        # performance is not possible
        row['performance'] = None
    else:
        row['performance'] = max(round(num / den, 4), 0)

    target = float(row['target']) if row['target'] else 0.0

    if not target or row['performance'] is None or row['volume_meeting_target'] is None or row['total_volume'] is None:
        # target is None or 0, or
        # performance is NaN, or
        # volume_meeting_target or total_volume are not defined,
        # target_met is not possible
        row['target_met'] = 'NA'

    # if performance >= target then target is met
    elif row['performance'] >= target:
        row['target_met'] = 'Y'

    # otherwise target_met is not met
    else:
        row['target_met'] = 'N'

    return row


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
        row = process_row(row)
        writer.writerow(row)


if __name__ == '__main__':
    main()
