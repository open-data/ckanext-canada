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
    Create a consolidated list of choices for ministers
    """
    existing_list = {}

    # fetch existing list, if it exists
    if os.path.isfile(OUTPUT_FILE):
        with open(OUTPUT_FILE) as json_file:
            try:
                existing_list = json.load(json_file)
            except ValueError as e:
                return False
        json_file.close()

    # generate a list of choices from external source
    choices = download_xml_from_source()

    # if existing list does not exist
    if not existing_list and choices:
        return set_status(choices)
    # if crawled choices list does not exist
    elif existing_list and not choices:
        return set_status(existing_list)
    # if both exist, compare both lists for changes
    elif existing_list and choices:
        for row in existing_list:
            if row in choices:
                # case: minister found in both lists
                # update minister if existing list is different from choices list
                if cmp(existing_list[row], choices[row]):
                    existing_list[row]['precedence'] = choices[row]['precedence']
                    for langCode in lang_codes:
                        existing_list[row][langCode] = choices[row][langCode]
                        existing_list[row]['honorific_title_' + langCode] = choices[row]['honorific_title_' + langCode]
                        # case: same minister with new position in choices, then append new position to existing list
                        for position in choices[row]['positions_' + langCode]:
                            if not [d for d in existing_list[row]['positions_' + langCode]
                                    if d['title_' + langCode] == position['title_' + langCode]]:
                                existing_list[row]['positions_' + langCode].append(position)
                            else:
                                # case: same minister with same position title but other details changed, then update
                                idx = next((index for (index, d) in enumerate(existing_list[row]['positions_' + langCode]) if d['title_' + langCode] == position['title_' + langCode]), None)
                                existing_list[row]['positions_' + langCode][idx].update(position)
                        # case: same minister with existing position not in choices then update end date as today
                        for position in existing_list[row]['positions_' + langCode]:
                            if not [d for d in choices[row]['positions_' + langCode]
                                    if d['title_' + langCode] == position['title_' + langCode]]:
                                position['end_date'] = date.today().strftime("%Y-%m-%dT%H:%M:%S")
            else:
                # case: minister found in existing list but now in new list, update end date as today
                for langCode in lang_codes:
                    for position in existing_list[row]['positions_' + langCode]:
                        position['end_date'] = date.today().strftime("%Y-%m-%dT%H:%M:%S")

        for row in choices:
            if row not in existing_list:
                # case: new minister in choices, add new minister to existing list
                existing_list[row] = choices[row]

        return set_status(existing_list)
    # both lists do not exist
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
        # url = 'https://www.ourcommons.ca/Parliamentarians/' + langCode + '/ministries/Export?output=XML'
        url = 'http://localhost/export-' + langCode + '.xml'
        response = requests.get(url, stream=True)

        # if valid response then save as xml tree
        if response.status_code == 200:
            xml_tree[langCode] = etree.fromstring(response.content)

            for row in xml_tree[langCode].xpath('Minister'):
                # gather name and position
                name = row.xpath('PersonOfficialFirstName/text()')[0] + ' ' + \
                       row.xpath('PersonOfficialLastName/text()')[0]
                position = {
                    'title_' + langCode: row.xpath('Title/text()')[0],
                    'start_date': row.xpath('FromDateTime/text()')[0],
                    'end_date': ''.join(row.xpath('ToDateTime/text()'))
                }
                # if name already exist in json
                if name in choices:
                    # add translation
                    if langCode not in choices[name]:
                        choices[name].update([
                            (langCode, row.xpath('PersonOfficialLastName/text()')[0] + ', '
                             + row.xpath('PersonOfficialFirstName/text()')[0]
                             + ' (' + row.xpath('PersonShortHonorific/text()')[0] + ')'),
                            ('honorific_title_' + langCode, row.xpath('PersonShortHonorific/text()')[0]),
                            ('positions_' + langCode, [position]),
                            ])
                    else:
                        # append position
                        choices[name]['positions_' + langCode].append(position)

                # new name in json
                else:
                    choices[name] = {
                        langCode: row.xpath('PersonOfficialLastName/text()')[0] + ', '
                        + row.xpath('PersonOfficialFirstName/text()')[0]
                        + ' (' + row.xpath('PersonShortHonorific/text()')[0] + ')',
                        'honorific_title_' + langCode: row.xpath('PersonShortHonorific/text()')[0],
                        'precedence': row.xpath('OrderOfPrecedence/text()')[0],
                        'positions_' + langCode: [position],
                    }
        response.close()
    return choices


def set_status(list):
    """
    Set status for list to determine if current vs former minister
    """
    status = 0
    for row in list:
        for position in list[row]['positions_en']:
            if not position['end_date']:
                status = 1
                break
        list[row]['status'] = status
    return list


# get list of choices and write to OUTPUT file as JSON
minister_list = get_filter_output()
if minister_list:
    open(OUTPUT_FILE, 'wb').write(json.dumps(
        minister_list,
        indent=2,
        separators=(',', ':'),
        sort_keys=True,
        ensure_ascii=False,
    ).encode('utf-8'))
    sys.stderr.write('wrote %d items\n' % len(minister_list))
else:
    sys.stderr.write('Unable to create ministers list\n')
