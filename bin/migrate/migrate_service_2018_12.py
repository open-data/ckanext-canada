#!/usr/bin/env python

import unicodecsv
import sys
import codecs
import json

FIELDNAMES = 'fiscal_yr,service_id,service_name_en,service_name_fr,external_internal,service_type,special_designations,service_description_en,service_description_fr,authority_en,authority_fr,service_url_en,service_url_fr,program_name_en,program_name_fr,program_id_code,client_target_groups,service_fee,cra_business_number,use_of_sin,online_applications,web_visits_info_service,calls_received,in_person_applications,email_applications,fax_applications,postal_mail_applications,e_registration,e_authentication,e_application,e_decision,e_issuance,e_feedback,client_feedback,special_remarks_en,special_remarks_fr,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8
sys.stdout.write(codecs.BOM_UTF8)

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

try:
    for line in in_csv:
        service_id = line.pop('service_id_number')
        y1, y2, org, num = service_id.split('-')
        line['service_id'] = unicode(int(num))
        line['fiscal_yr'] = '2016-2017'  # all existing reports from this year

        line['program_id_code'] = line.pop('program_id_number')
        line['service_fee'] = line.pop('user_fee')
        line['online_applications'] = line.pop('volumes_per_channel_online')
        line['calls_received'] = line.pop('volumes_per_channel_telephone')
        line['in_person_applications'] = line.pop('volumes_per_channel_in_person')
        line['postal_mail_applications'] = line.pop('volumes_per_channel_mail')

        del line['responsibility_area_en']
        del line['responsibility_area_fr']
        del line['service_owner']
        del line['service_agreements']
        del line['targets_published_en']
        del line['targets_published_fr']
        del line['interaction_points_online']
        del line['interaction_points_total']
        del line['percentage_online']

        line['service_url_en'] = ''
        line['service_url_fr'] = ''
        line['use_of_sin'] = ''
        line['web_visits_info_service'] = ''
        line['email_applications'] = ''
        line['fax_applications'] = ''
        line['client_feedback'] = ''

        out_csv.writerow(line)

except KeyError:
    if 'warehouse' in sys.argv:
        sys.exit(85)
    else:
        raise
