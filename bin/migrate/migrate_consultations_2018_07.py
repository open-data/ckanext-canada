#!/usr/bin/env python

import unicodecsv
import sys
import codecs
import json

FIELDNAMES = 'registration_number,publishable,partner_departments,subjects,title_en,title_fr,description_en,description_fr,target_participants_and_audience,start_date,end_date,status,profile_page_en,profile_page_fr,report_available_online,report_link_en,report_link_fr,contact_email,policy_program_lead_email,remarks_en,remarks_fr,high_profile,rationale,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8
sys.stdout.write(codecs.BOM_UTF8)

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

RATIONALE = {
    'B16': 'BG',
    'B17': 'BG',
    'B18': 'BG',
}

try:
    for line in in_csv:
        del line['sector']
        del line['goals']
        del line['public_opinion_research']
        del line['public_opinion_research_standing_offer']
        line['start_date'] = line.pop('planned_start_date')
        line['end_date'] = line.pop('planned_end_date')
        line['profile_page_en'] = line.pop('further_information_en')
        line['profile_page_fr'] = line.pop('further_information_fr')
        line['partner_departments'] = ','.join(
            'D' + d for d in line['partner_departments'].split(',') if d)
        line['high_profile'] = 'N' if 'NH' in line['rationale'].split(',') else 'Y'
        line['rationale'] = ','.join(
            RATIONALE.get(r, r) for r in line['rationale'].split(',') if r != 'NH')
        line['subjects'] = ','.join(
            s for s in line['subjects'].split(',') if s != 'FP')
        out_csv.writerow(line)

except KeyError:
    if 'warehouse' in sys.argv:
        sys.exit(85)
    else:
        raise
