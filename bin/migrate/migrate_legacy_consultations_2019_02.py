#!/usr/bin/env python

import unicodecsv
import sys
import codecs
import os
from datetime import datetime

import yaml

SUBJECT_CHOICES_FILE = os.path.join(
    os.path.dirname(__file__), '../../ckanext/canada/tables/choices/consultation_subject.yaml')

FIELDNAMES = 'registration_number,publishable,partner_departments,subjects,title_en,title_fr,description_en,description_fr,target_participants_and_audience,start_date,end_date,status,profile_page_en,profile_page_fr,report_available_online,report_link_en,report_link_fr,contact_email,policy_program_lead_email,remarks_en,remarks_fr,high_profile,rationale,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')

ORG_MAP = {
    'Fisheries and Oceans Canada': 'dfo-mpo',
    'Health Canada': 'hc-sc',
    'Canadian Nuclear Safety Commission': 'cnsc-ccsn',
    'Canadian Environmental Assessment Agency': 'ceaa-acee',
    'Canada Border Services Agency': 'cbsa-asfc',
    'Canadian Food Inspection Agency': 'cfia-acia',
    'Public Safety and Emergency Preparedness Canada': 'ps-sp',
    'Employment and Social Development Canada': 'esdc-edsc',
    'Public Works and Government Services Canada': 'pwgsc-tpsgc',
    'Statistics Canada': 'statcan',
    'Finance Canada': 'fin',
    'Indigenous and Northern Affairs Canada': 'aandc-aadnc',
    'Innovation, Science and Economic Development Canada': 'ic',
    'Global Affairs Canada': 'dfatd-maecd',
    'Transport Canada': 'tc',
    'Natural Resources Canada': 'nrcan-rncan',
    'Treasury Board of Canada, Secretariat': 'tbs-sct',
    'Parks Canada Agency': 'pc',
    'Canadian Transportation Agency': 'cta-otc',
    'Financial Consumer Agency of Canada': 'fcac-acfc',
    'National Energy Board': 'neb-one',
    'Atlantic Canada Opportunities Agency': 'acoa-apeca',
    'Canadian Grain Commission': 'cgc-ccg',
    'Veterans Affairs Canada': 'vac-acc',
    'Canada Revenue Agency': 'cra-arc',
    'Agriculture and Agri-Food Canada': 'aafc-aac',
    'Environment and Climate Change Canada': 'ec',
    'Shared Services Canada': 'ssc-spc',
    'Canadian Heritage': 'pch',
    'Patented Medicine Prices Review Board': 'pmprb-cepmb',
    'Canada Mortgage and Housing Corporation': 'cmhc-schl',
    'House of Commons': '',
    'Canadian Institutes of Health Research': 'cihr-irsc',
    'Infrastructure Canada': 'infc',
    'Immigration, Refugees and Citizenship Canada': 'cic',
    'National Defence': 'dnd-mdn',
    'Standards Council of Canada': 'scc-ccn',
    'National Parole Board': 'pbc-clcc',
    'Canada Economic Development': 'ced-dec',
    'Canadian Radio-Television and Telecommunications Commission': 'crtc',
    'Public Health Agency of Canada': 'phac-aspc',
    'Canadian Northern Economic Development Agency': 'cannor',
    'Justice Canada, Department of': 'jus',
    'Correctional Service Canada': 'csc-scc',
}

SUBJ_MAP = {
    v['en']: k for (k, v) in yaml.load(open(SUBJECT_CHOICES_FILE)).items()
}

def dt(legacy_date):
    return datetime.strptime(legacy_date, '%d-%m-%Y').strftime('%Y-%m-%d')

def main():
    in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')

    sys.stdout.write(codecs.BOM_UTF8)
    out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
    out_csv.writeheader()

    for line in in_csv:
        try:
            row = {
                'registration_number': 'A-%06d' % int(line['ID']),
                'title_en': line['title_en'],
                'title_fr': line['title_fr'],
                'description_en': line['description_en'],
                'description_fr': line['description_fr'],
                'start_date': dt(line['startdate']),
                'end_date': dt(line['enddate']),
                'report_link_en': line['urladdress_en'],
                'report_link_fr': line['urladdress_fr'],
                'owner_org': ORG_MAP[line['department_en']],
                'owner_org_title': '',
                'subjects': ','.join(SUBJ_MAP[s] for s in line['subjects_en'].split(' | ')),
            }
            out_csv.writerow(row)
        except KeyError as err:
            sys.stderr.write(line['ID'] + ': ' + str(err) + '\n')

main()
