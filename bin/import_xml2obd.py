#!/usr/bin/env python
'''
Usage:
    import_xml2_obd.py <xml file> <organizations json file> <presets.yaml> > <jsonl file>
    import_xml2obd.py upload <site_url> <api_key> <jsonl file> <doc directory>
'''
import argparse
import os
import time
from datetime import datetime
import sys
import json
from collections import defaultdict, OrderedDict
from lxml import etree
import yaml
import uuid

import ckanapi
import ckan
from ckanapi.errors import CKANAPIError
import traceback

presets = None
audience = None
canada_resource_type = None
canada_subject = None
canada_resource_language = None


def read_presets(filename):
    with open(filename, 'r') as f:
        _presets = yaml.load(f)
    return _presets


def read_json(filename):
    content=[]
    with open(filename) as f:
        for line in f:
            rec = json.loads(line)
            content.append(rec)
    return content


def read_xml(filename):
    root = etree.parse(filename).getroot()
    i = 0
    refs, extras = {}, {}
    assert(root.tag=="enterpriseLibrary")


    variant = root.find('application').find('parent').find('item').find(
                    'variants').find('variant')
    start = variant.find('properties')

    for l in start.findall('property'):
        if l.find('value').text:
            refs[l.attrib['name']] = l.find('value').text
    for c in start.findall('propertyGroup'):
        assert(c.attrib['name'] == 'customMetadata')
        for row in c.findall('propertyRow'):
            r = {}
            for l in row.findall('property'):
                r[l.attrib['name']] = l.find('value').text
            if r['metadata']:
                extras.update(r)

    return refs, extras


def desc(k,v):
    if 'English' in k:
        sub_key='en'
    elif 'French' in k:
        sub_key='fr'
    else:
        raise Exception('no such desc')
    return 'notes_translated', {sub_key:v}


def title(k,v):
    if 'English' in k:
        sub_key='en'
    elif 'French' in k:
        sub_key='fr'
    else:
        raise Exception('no such desc')
    return 'title_translated', {sub_key:v}

organizations = {}


def read_organizations_from_json(filename):
    with open(filename) as f:
        for line in f:
            rec = json.loads(line)
            title = rec['title'].split('|')[0].strip()
            organizations[title] = rec['id']
    assert(len(organizations)>100)


def owner_org(k,v):
    v = v.split('|')[0].strip()
    if v =='Public Works and Government Services Canada':
        v='Public Services and Procurement Canada'
    id = organizations.get(v, None)
    if not id:
        raise Exception('No such organiztion ' + v)
    return 'owner_org', id


def _get_choices_value(preset, val):
    name = preset['field_name']
    res = []
    for item in preset['choices']:
        for label in item['label'].values():
            if label in val:
                res.append(item['value'])
                break
    return name, res


def _get_single_choices_value(preset, val):
    name = preset['field_name']
    res = []
    for item in preset['choices']:
        for label in item['label'].values():
            if label in val:
                res.append(item['value'])
                break
    return name, res[0]

xml2obd=OrderedDict([
    ('Description English', desc),
    ('Description French', desc),
    ('Title English', title),
    ('Title French', title),
    ('Audience', lambda k,v: _get_choices_value(audience, v),),
    ('Subject', lambda k,v: _get_choices_value(canada_subject, v),),
    ('Publisher Organization', owner_org),

    ('Date Created', lambda k, v: ('metadata_created',v)),
    ('Date Modified', lambda k, v: ('metadata_modified',v)),
    ('Classification Code', lambda k, v: ('doc_classification_code',v)),
    ('Creator', lambda k, v: ('author',v)),
    ('retentionTrigger', None),
    ('retentionPeriod', None),
    ('Status Date', None),
])

xml2resource={
    'Resource Type': lambda k,v: _get_single_choices_value(canada_resource_type, v),
    'Record Date': lambda k,v: ('created', v),
    'Unique ID': lambda k,v: ('unique_identifier', v),
    'Language': lambda k,v: _get_choices_value(canada_resource_language, v),
}


def xml_obd_mapping(dict_data, map_dict):
    res = {}
    for k,f in map_dict.iteritems():
        if k in dict_data:
            v = dict_data[k]
            dict_data.pop(k)
            if not f:
                continue
            new_key, new_val = f(k,v)
            val = res.get(new_key, None)
            if isinstance(val,dict):
                val.update(new_val)
            elif isinstance(val, list):
                for _val in new_val:
                    val.append(_val)
            elif not new_val:
                pass
            else:
                res[new_key] = new_val
    return res


def get_preset(name):
    for it in presets['presets']:
        if it['preset_name']==name:
            return it['values']
    return None


def upload_resources(remote_site, api_key, jsonfile, resource_directory):
    #remote site
    site = ckanapi.RemoteCKAN(
        remote_site,
        apikey=api_key,
        user_agent='ckanapi-uploader/1.0')

    #load dataset and resource file to cloud
    ds = read_json(jsonfile)
    for rec in ds:
        try:
            #site.action.package_delete(id=rec['id'])
            #return
            #site.action.package_create(**rec)
            site.action.package_update(**rec)
        except ckan.logic.NotFound:
            try:
                site.action.package_create(**rec)
            except ckan.logic.ValidationError:
                traceback.print_exc()
                print(rec)
                continue
        except ckan.logic.ValidationError:
            traceback.print_exc()
            print(rec)
            continue
        res = rec['resources'][0]
        source = resource_directory + '/' + res['url'].split('/')[-1]
        with open(source) as f:
            try:
                rc = site.action.resource_patch(
                    id=res['id'],
                    upload=(os.path.basename(source), f))
            except ckanapi.errors.CKANAPIError:
                traceback.print_exc()
                print(rec)
                print("failed upload " + os.path.basename(source))
                continue

        print("updated for " + os.path.basename(source))


def main():
    global presets, audience, canada_resource_type,canada_subject
    global canada_resource_language
    canada_resource_format = None

    # upload the generated json to remote site and upload the file
    if sys.argv[1] =='upload':
        return upload_resources(*sys.argv[2:])

    refs, extras = read_xml(sys.argv[1])
    read_organizations_from_json(sys.argv[2])
    presets = read_presets(sys.argv[3])  # TODO: read from doc.yaml
    audience = get_preset('canada_audience')
    canada_resource_type = get_preset('canada_resource_type')
    canada_subject = get_preset('canada_subject')
    canada_resource_language = get_preset('canada_resource_language')
    canada_resource_format = map(lambda x:x['value'],
                                 get_preset('canada_resource_format')['choices'])

    ds = xml_obd_mapping(refs, xml2obd)
    ds['collection'] = 'publication'
    release_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not ds.get('date_published'):
        ds['date_published'] = release_date
    ds['id'] = str(uuid.uuid5(uuid.NAMESPACE_URL,
                   'http://dev.obd.ca/' + sys.argv[1]))
    ds['name'] = ds['id']
    ds['title'] = ds['title_translated']['en']
    ds['state'] = 'active'
    ds['type'] = 'doc'
    ds['license_id'] = "ca-ogl-lgo"
    if not ds.get('owner_org', None):
        ds['owner_org'] = "A0F0FCFC-BC3B-4696-8B6D-E7E411D55BAC"
    if not ds.get('keywords', None):
        ds['keywords']={'en':['statcan'], 'fr':['statcan']}
    if not ds.get('subject', None):
        ds['subject'] = ["information_and_communications"]
    if not ds.get('notes_translated', None):
        ds['notes_translated'] = {'en':'n/a', 'fr':'n/a'}
    if not ds['notes_translated'].get('fr', None):
        ds['notes_translated']['fr'] = ds['notes_translated']['en']
    if not ds['title_translated'].get('fr', None):
        ds['title_translated']['fr'] = ds['title_translated']['en']

    res = xml_obd_mapping(refs, xml2resource)
    res_name = sys.argv[1].split('/')[-1][:-4]
    res['name_translated']={'en':res_name, 'fr':res_name}
    res['id'] = str(uuid.uuid5(uuid.NAMESPACE_URL,
                    'http://dev.obd.ca/resources/' + sys.argv[1]))
    res['url'] = 'http://dev.obd.ca/' + sys.argv[1].split('/')[-1][:-4]
    res['format'] = sys.argv[1].split('/')[-1].split('.')[-2].upper()
    if res['format'] not in canada_resource_format:
        res['format'] = 'other'
    if not res.get('language'):
        res['language'] = ['en']
    if not res.get('resource_type'):
        res['resource_type']='guide'
    ds['resources'] = [res]
    print(json.dumps(ds))

if __name__=='__main__':
    main()
