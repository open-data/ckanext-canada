#!/usr/bin/env python3

import sys
import csv
import codecs

assert sys.stdin.read(3) == codecs.BOM_UTF8

reader = csv.DictReader(sys.stdin)
writer = csv.DictWriter(sys.stdout, fieldnames=
'reference_number,procurement_id,vendor_name,vendor_postal_code,buyer_name,contract_date,economic_object_code,description_en,description_fr,contract_period_start,delivery_date,contract_value,original_value,amendment_value,comments_en,comments_fr,additional_comments_en,additional_comments_fr,agreement_type_code,trade_agreement,land_claims,commodity_type,commodity_code,country_of_origin,solicitation_procedure,limited_tendering_reason,trade_agreement_exceptions,indigenous_business,indigenous_business_excluding_psib,intellectual_property,potential_commercial_exploitation,former_public_servant,contracting_entity,standing_offer_number,instrument_type,ministers_office,number_of_bids,article_6_exceptions,award_criteria,socioeconomic_indicator,reporting_period,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')
])
writer.writeheader()

try:
    for row in reader:
        row['indigenous_business'] = row.pop('aboriginal_business')
        row['indigenous_business_excluding_psib'] = row.pop('aboriginal_business_incidental')
        writer.writerow(row)

except KeyError:
    if 'warehouse' in sys.argv:
        sys.exit(85)
    else:
        raise
