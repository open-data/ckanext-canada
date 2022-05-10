#!/usr/bin/env python

import unicodecsv
import sys
import codecs
import os
from datetime import datetime

import yaml

FIELDNAMES = 'registration_number,publishable,partner_departments,subjects,title_en,title_fr,description_en,description_fr,target_participants_and_audience,start_date,end_date,status,profile_page_en,profile_page_fr,report_available_online,report_link_en,report_link_fr,contact_email,policy_program_lead_email,remarks_en,remarks_fr,high_profile,rationale,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')

ORG_MAP = {
    'Agriculture and Agri-Food Canada': 'aafc-aac',
    'Atlantic Canada Opportunities Agency': 'acoa-apeca',
    'Canada Border Services Agency': 'cbsa-asfc',
    'Canada Economic Development': 'ced-dec',
    'Canada Mortgage and Housing Corporation': 'cmhc-schl',
    'Canada Revenue Agency': 'cra-arc',
    'Canadian Environmental Assessment Agency': 'ceaa-acee',
    'Canadian Food Inspection Agency': 'cfia-acia',
    'Canadian Grain Commission': 'cgc-ccg',
    'Canadian Heritage': 'pch',
    'Canadian Institutes of Health Research': 'cihr-irsc',
    'Canadian Northern Economic Development Agency': 'cannor',
    'Canadian Nuclear Safety Commission': 'cnsc-ccsn',
    'Canadian Radio-Television and Telecommunications Commission': 'crtc',
    'Canadian Transportation Agency': 'cta-otc',
    'Correctional Service Canada': 'csc-scc',
    'Employment and Social Development Canada': 'esdc-edsc',
    'Environment and Climate Change Canada': 'ec',
    'Finance Canada': 'fin',
    'Financial Consumer Agency of Canada': 'fcac-acfc',
    'Fisheries and Oceans Canada': 'dfo-mpo',
    'Global Affairs Canada': 'dfatd-maecd',
    'Health Canada': 'hc-sc',
    'House of Commons': 'hoc-cdc',
    'Immigration, Refugees and Citizenship Canada': 'cic',
    'Indigenous and Northern Affairs Canada': 'aandc-aadnc',
    'Infrastructure Canada': 'infc',
    'Innovation, Science and Economic Development Canada': 'ic',
    'Justice Canada, Department of': 'jus',
    'National Defence': 'dnd-mdn',
    'National Energy Board': 'neb-one',
    'National Parole Board': 'pbc-clcc',
    'Natural Resources Canada': 'nrcan-rncan',
    'Parks Canada Agency': 'pc',
    'Patented Medicine Prices Review Board': 'pmprb-cepmb',
    'Public Health Agency of Canada': 'phac-aspc',
    'Public Safety and Emergency Preparedness Canada': 'ps-sp',
    'Public Works and Government Services Canada': 'pwgsc-tpsgc',
    'Shared Services Canada': 'ssc-spc',
    'Standards Council of Canada': 'scc-ccn',
    'Statistics Canada': 'statcan',
    'Transport Canada': 'tc',
    'Treasury Board of Canada, Secretariat': 'tbs-sct',
    'Veterans Affairs Canada': 'vac-acc',
}

SUBJ_MAP = {
    'Advertising / Marketing': 'AD',
    'Agriculture': 'AG',
    'Amendments': 'AM',
    'Animals': 'AN',
    'Arts': 'AA',
    'Children': 'CD',
    'Communication': 'CM',
    'Copyright / Trademarks / Patents': 'CR',
    'Culture': 'CU',
    'Development': 'DV',
    'Economic development': 'ED',
    'Economy': 'EC',
    'Education': 'EU',
    'Employment': 'EM',
    'Environment': 'EN',
    'Exporting/Importing': 'EX',
    'Finance': 'FI',
    'Financial assistance and entitlements': 'FA',
    'Fisheries': 'FS',
    'Food and drug': 'FD',
    'Foreign affairs': 'FO',
    'Foreign policy': 'FO',  # NB: merged with Foreign affairs
    'Government procurement': 'GP',
    'Health': 'HS',
    'Heritage': 'HP',
    'Housing': 'HL',
    'Human resources': 'HR',
    'Immigration': 'IM',
    'Indigenous Peoples': 'AP',
    'Industry': 'IN',
    'International': 'IT',
    'Justice and the Law': 'JL',
    'Labour': 'LT',
    'National defence': 'ND',
    'Natural resources': 'NR',
    'Persons with disabilities': 'PD',
    'Plants': 'PL',
    'Policy': 'PO',
    'Private sector': 'PR',
    'Public safety': 'PS',
    'Recreation': 'RL',
    'Regulations': 'RE',
    'Rural and remote services': 'RU',
    'Science and technology': 'ST',
    'Seniors': 'SA',
    'Service': 'SE',
    'Society': 'SO',
    'Sport': 'SP',
    'Taxes': 'TX',
    'Trade': 'TC',
    'Training and careers': 'TF',
    'Transportation': 'TR',
    'Youth': 'YJ',
}

def dt(legacy_date):
    d = datetime.strptime(legacy_date, '%d-%m-%Y')
    assert d < datetime(2018,1,1), d
    return d.strftime('%Y-%m-%d')

def main():
    assert sys.stdin.read(3) == codecs.BOM_UTF8
    sys.stdout.write(codecs.BOM_UTF8)

    try:
        in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')

        orgs = {}
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
                    'profile_page_en': line['urladdress_en'],
                    'profile_page_fr': line['urladdress_fr'],
                    'owner_org': ORG_MAP[line['department_en']],
                    'owner_org_title': '',
                    'subjects':
                        ','.join(SUBJ_MAP[s] for s in line['subjects_en'].split(' | '))
                        if line['subjects_en'] else '',
                    'user_modified': '*',  # special "we don't know" value
                    'publishable': 'Y',
                    'report_available_online': 'N',
                    'high_profile': 'N',
                    'status': 'CN',
                }
                if not row['title_fr']:
                    sys.stderr.write(line['ID'] + ': missing title_fr\n')
                else:
                    orgs.setdefault(row['owner_org'], []).append(row)
            except KeyError as err:
                sys.stderr.write(line['ID'] + ': ' + str(err) + '\n')

        out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
        out_csv.writeheader()
        for o in sorted(orgs):
            for row in orgs[o]:
                out_csv.writerow(row)

    except KeyError:
        if 'warehouse' in sys.argv:
            sys.exit(85)
        else:
            raise
main()
