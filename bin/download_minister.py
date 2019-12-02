#!/usr/bin/env python
# coding=utf-8

import unicodecsv
import requests
import json
import sys
import os.path
from lxml import etree
from operator import itemgetter

OUTPUT_FILE = os.path.join(os.path.split(__file__)[0],
                           '../ckanext/canada/tables/choices/minister.json')
choices = {}


def download_csv_filter_output(session_id):
    """
    Read XML to generate JSON choices
    """
    lang_codes = ["en", "fr"]
    responses = {}
    is_valid = False

    for langCode in lang_codes:
        url = 'https://www.ourcommons.ca/members/' + langCode + '/ministries/xml?ministry=' + str(session_id)
        response = requests.get(url, stream=True)
        responses[langCode] = response

    if responses['en'].status_code == 200 and responses['fr'].status_code == 200:
        xml_en = etree.fromstring(responses['en'].content)
        xml_fr = etree.fromstring(responses['fr'].content)

        for row in xml_en.xpath('Minister'):
            is_valid = True
            name = row.xpath('PersonOfficialFirstName/text()')[0] + ' ' + row.xpath('PersonOfficialLastName/text()')[0]
            choices[name] = {
                'en': row.xpath('PersonShortHonorific/text()')[0] + ' ' + name + ' - ' + row.xpath('Title/text()')[0],
                'precedence': row.xpath('OrderOfPrecedence/text()')[0],
                'title_en': row.xpath('Title/text()')[0],
                'honorific_title_en': row.xpath('PersonShortHonorific/text()')[0],
                'start_date': row.xpath('FromDateTime/text()')[0],
                'end_date': '' . join(row.xpath('ToDateTime/text()')),
            }

            for row_fr in xml_fr.xpath('Minister'):
                name_fr = row_fr.xpath('PersonOfficialFirstName/text()')[0] \
                          + ' ' \
                          + row_fr.xpath('PersonOfficialLastName/text()')[0]
                if name == name_fr:
                    choices[name].update([('fr', row_fr.xpath('PersonShortHonorific/text()')[0] + ' '
                                           + name + ' - ' + row_fr.xpath('Title/text()')[0]),
                                          ('title_fr', row_fr.xpath('Title/text()')[0]),
                                          ('honorific_title_fr', row_fr.xpath('PersonShortHonorific/text()')[0])])
                    break

    for langCode in lang_codes:
        responses[langCode].close()

    return is_valid


# first session for publishing according to Bill C-58
sessionId = 28
while download_csv_filter_output(sessionId):
    sessionId += 1

open(OUTPUT_FILE, 'wb').write(json.dumps(
    choices,
    indent=2,
    separators=(',', ':'),
    sort_keys=True,
    ensure_ascii=False,
).encode('utf-8'))
sys.stderr.write('wrote %d items\n' % len(choices))
