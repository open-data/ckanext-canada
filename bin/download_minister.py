#!/usr/bin/env python
# coding=utf-8

import unicodecsv
import requests
import json
import sys
import os.path
from lxml import etree
from operator import itemgetter
from datetime import date

OUTPUT_FILE = os.path.join(os.path.split(__file__)[0],
                           '../ckanext/canada/tables/choices/minister.json')
lang_codes = ["en", "fr"]


def get_filter_output():
    """
    Create consolidated choices for ministries
    """
    existing_choices = {}

    # fetch existing choices file, if it exists
    if os.path.isfile(OUTPUT_FILE):
        with open(OUTPUT_FILE) as json_file:
            try:
                existing_choices = json.load(json_file)
            except ValueError:
                return False
        json_file.close()

    # generate choices from external source
    choices = download_xml_from_source()

    # if existing choices file does not exist
    if not existing_choices and choices:
        return choices
    # if crawled choices do not exist
    elif existing_choices and not choices:
        return existing_choices
    # if both exist, compare choices for changes
    elif existing_choices and choices:
        for row in existing_choices.keys():
            if row in choices:
                # make sure same position title for the position code
                if existing_choices[row]['en'] == choices[row]['en']:
                    # position found in both
                    if existing_choices[row] != choices[row]:
                        # case: same position with new minister in choices, then add new minister to existing position
                        # and update end date as today for existing ministers
                        for minister in existing_choices[row]['ministers']:
                            if minister['name'] != choices[row]['ministers'][0]['name']:
                                minister['end_date'] = date.today().strftime("%Y-%m-%dT%H:%M:%S")
                        else:
                            existing_choices[row]['ministers'].insert(0, choices[row]['ministers'][0])
            else:
                # case: position found in existing choices but now in choices,
                # update end date as today for all ministers
                for minister in existing_choices[row]['ministers']:
                    minister['end_date'] = date.today().strftime("%Y-%m-%dT%H:%M:%S")

        for row in choices:
            if not [d for d in existing_choices if existing_choices[d]['en'] == choices[row]['en']]:
                # case: new position in choices, add new position to existing choices
                # and resolve duplicate codes, if required
                position_code = row
                i = 0
                while position_code in existing_choices:
                    i += 1
                    position_code = row + str(i)
                existing_choices[position_code] = choices[row]

        return existing_choices
    # both choices and existing choices do not exist
    else:
        return False


def download_xml_from_source():
    """
    Read XML from external source to generate JSON choices for ministers
    """
    choices = {}
    xml_tree = {}

    # collect responses for both languages
    for langCode in lang_codes:
        try:
            url = 'https://www.ourcommons.ca/Parliamentarians/' + langCode + '/ministries/Export?output=XML'
            response = requests.get(url, stream=True)
            xml_tree[langCode] = etree.fromstring(response.content)
            response.close()
        except requests.exceptions.RequestException:
            return False

    iter_fr = iter(xml_tree['fr'].xpath('Minister'))

    for row_en in xml_tree['en'].xpath('Minister'):
        row_fr = next(iter_fr)
        # set name
        name = row_en.xpath('PersonOfficialFirstName/text()')[0] + ' ' + \
               row_en.xpath('PersonOfficialLastName/text()')[0]
        # set position code with position initials
        position_code = (''.join([x[0].upper() for x in row_en.xpath('Title/text()')[0].split(' ')]))
        # set minister
        minister = {
            'name': name,
            'name_en': row_en.xpath('PersonOfficialLastName/text()')[0] + ', '
                       + row_en.xpath('PersonOfficialFirstName/text()')[0]
                       + ' (' + row_en.xpath('PersonShortHonorific/text()')[0] + ')',
            'name_fr': row_fr.xpath('PersonOfficialLastName/text()')[0] + ', '
                       + row_fr.xpath('PersonOfficialFirstName/text()')[0]
                       + ' (' + row_fr.xpath('PersonShortHonorific/text()')[0] + ')',
            'start_date': row_en.xpath('FromDateTime/text()')[0],
            'end_date': ''.join(row_en.xpath('ToDateTime/text()')),
            'precedence': row_en.xpath('OrderOfPrecedence/text()')[0],
        }

        # resolve duplicate position codes
        i = 0
        while position_code in choices:
            i += 1
            position_code = position_code + str(i)

        # add position to dict
        choices[position_code] = {
            'en': row_en.xpath('Title/text()')[0],
            'fr': row_fr.xpath('Title/text()')[0],
            'ministers': [minister],
        }

    return choices


# get choices and write to OUTPUT file as JSON
minister_choices = get_filter_output()
if minister_choices:
    open(OUTPUT_FILE, 'wb').write(json.dumps(
        minister_choices,
        indent=2,
        separators=(',', ':'),
        sort_keys=True,
        ensure_ascii=False,
    ).encode('utf-8'))
    sys.stderr.write('wrote %d items\n' % len(minister_choices))
else:
    sys.stderr.write('Unable to create ministers choices\n')
