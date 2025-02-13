#!/usr/bin/env python3
# coding=utf-8

import json
import sys
import os.path
from datetime import date
from urllib.request import urlopen
from bs4 import BeautifulSoup
import re

OUTPUT_FILE = os.path.join(
                os.path.split(__file__)[0],
                '../ckanext/canada/tables/choices/minister.json')
lang_codes = ["en", "fr"]
all_mp_urls = []


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

    # generate choices from external source
    choices = download_from_source()

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
                        # case: same position with new minister in choices,
                        # then add new minister to existing position
                        # and update end date for existing ministers
                        for minister in existing_choices[row]['ministers']:
                            if (
                              minister['name'] != choices[row]['ministers'][0]['name']
                              and not minister['end_date']):

                                minister['end_date'] = get_end_date(
                                                        minister['name'],
                                                        existing_choices[row]['en'])
                        else:
                            if (
                              existing_choices[row]['ministers'][0] !=
                              choices[row]['ministers'][0]):

                                existing_choices[row]['ministers'].insert(
                                    0,
                                    choices[row]['ministers'][0])
            else:
                # case: position found in existing
                # choices but not in choices,
                # update end date for all ministers
                for minister in existing_choices[row]['ministers']:
                    if not minister['end_date']:
                        minister['end_date'] = get_end_date(minister['name'],
                                                            existing_choices[row]['en'])

        for row in choices:
            if not [d for d in existing_choices
                    if existing_choices[d]['en'] == choices[row]['en']]:
                # case: new position in choices,
                # add new position to existing choices
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


def download_from_source():
    choices = {}
    ministers_list = get_ministries_list()

    # set position code with position initials
    for p in ministers_list:
        # set position code with position initials
        position_title = p['title_en'].split(' ')
        position_code = ''
        for initial in position_title:
            if initial not in ('and', 'the', 'is', 'of', 'with', 'for', 'in'):
                position_code += initial[0].upper()

        # resolve duplicate position codes
        i = 0
        while position_code in choices:
            i += 1
            position_code = position_code + str(i)

        # add position to dict
        choices[position_code] = {
            u'en': p['title_en'],
            u'fr': p['title_fr'],
            u'ministers': [{
                u'name': p['name'],
                u'name_en': p['name_en'],
                u'name_fr': p['name_fr'],
                u'start_date': p['start_date'],
                u'end_date': p['end_date'],
            }],
        }
    return choices


def get_ministries_list():
    cabinet_ministers_list = []
    url = 'https://www.ourcommons.ca/Members/en/ministries'
    page = urlopen(url)
    html = page.read().decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    for minister in soup.find_all(id=re.compile("^mp-tile-person-id")):
        minister_url = minister.find('a')['href']
        minister_positions = []
        positions = minister.find_all('div', class_='')
        for position in positions:
            minister_positions.append(position.text)
        minister_positions = filter(None, minister_positions)
        current_positions = get_parliamentary_position_roles(
            'https://www.ourcommons.ca' + minister_url + '/roles/xml',
            minister_positions)
        cabinet_ministers_list.extend(current_positions)
    return cabinet_ministers_list


def get_parliamentary_position_roles(url, positions=None):
    print(url, positions)
    url_fr = url.replace('/en/', '/fr/')
    member_roles = []

    page = urlopen(url)
    page_fr = urlopen(url_fr)
    xml = page.read().decode('utf-8')
    xml_fr = page_fr.read().decode('utf-8')
    soup = BeautifulSoup(xml, 'xml')
    soup_fr = BeautifulSoup(xml_fr, 'xml')

    hon = soup.find('PersonShortHonorific').text
    hon_fr = soup_fr.find('PersonShortHonorific').text
    firstname = soup.find('PersonOfficialFirstName').text
    lastname = soup.find('PersonOfficialLastName').text

    for role in soup.find_all('ParliamentaryPositionRole'):
        member_roles.append({
            u'title_en': role.find('Title').text,
            u'name': firstname + ' ' + lastname,
            u'name_en': lastname + ', ' + firstname + ' (' + hon + ')',
            u'name_fr': lastname + ', ' + firstname + ' (' + hon_fr + ')',
            u'start_date': role.find('FromDateTime').text,
            u'end_date': role.find('ToDateTime').text,
        })
    i = 0
    for role_fr in soup_fr.find_all('ParliamentaryPositionRole'):
        member_roles[i]['title_fr'] = next(role_fr.children).text.capitalize()
        i += 1

    if positions:
        current_positions = [p for p in member_roles
                             if p['title_en'] in positions and not p['end_date']]
        return current_positions

    return member_roles


def get_end_date(name, position):
    global all_mp_urls
    if not len(all_mp_urls):
        # get url for all mps
        all_mps_page = urlopen(
            'https://www.ourcommons.ca/Members/en/search'
            '?parliament=all&caucusId=all&province=all&gender=all')
        all_mps_html = all_mps_page.read().decode('utf-8')
        all_mps_soup = BeautifulSoup(all_mps_html, 'html.parser')
        all_mp_urls = all_mps_soup.find_all(class_='ce-mip-mp-tile')

    for m in all_mp_urls:
        if m.find(class_='ce-mip-mp-name', text=name):
            roles = get_parliamentary_position_roles(
                'https://www.ourcommons.ca' + m['href'] + '/roles/xml')
            for r in roles:
                if r['title_en'] == position:
                    return r['end_date']
    return date.today().strftime("%Y-%m-%dT%H:%M:%S")


# get choices and write to OUTPUT file as JSON
minister_choices = get_filter_output()

# add Governor General to the list to make a combined
# list for admin_aircraft and qpnotes
minister_choices['GG'] = {
    "en": "The Governor General of Canada",
    "fr": "La gouverneure générale du Canada",
    "ministers": [
        {
            "end_date": "",
            "name": "Mary Simon",
            "name_en": "Simon, Mary (Right Hon.)",
            "name_fr": "Simon, Mary (Le très hon.)",
            "start_date": "2021-07-26T08:00:00"
        }
    ]
}

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
    sys.exit(1)
