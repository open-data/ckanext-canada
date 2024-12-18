#!/usr/bin/env python
# coding=utf-8

import requests
import pandas as pd
import io

pd_list = { 'briefingt': { 'url' : 'https://open.canada.ca/data/dataset/ee9bd7e8-90a5-45db-9287-85c8cf3589b6/resource/299a2e26-5103-4a49-ac3a-53db9fcc06c7/download/briefingt.csv','key' : ['tracking_number'],},
            'hospitalityq': { 'url': 'https://open.canada.ca/data/dataset/b9f51ef4-4605-4ef2-8231-62a2edda1b54/resource/7b301f1a-2a7a-48bd-9ea9-e0ac4a5313ed/download/hospitalityq.csv', 'key': ['ref_number'], },
            'qpnotes': { 'url' : 'https://open.canada.ca/data/dataset/ecd1a913-47da-47fc-8f96-2432be420986/resource/c55a2862-7ec4-462c-a844-22acab664812/download/qpnotes.csv', 'key' : ['reference_number'], },
            'travela': { 'url' : 'https://open.canada.ca/data/dataset/4ae27978-0931-49ab-9c17-0b119c0ba92f/resource/a811cac0-2a2a-4440-8a81-2994fc753171/download/travela.csv', 'key': ['year'], },
            'travelq': { 'url' : 'https://open.canada.ca/data/dataset/009f9a49-c2d9-4d29-a6d4-1a228da335ce/resource/8282db2a-878f-475c-af10-ad56aa8fa72c/download/travelq.csv', 'key' : ['ref_number'], },
            'travelq-nil': { 'url' : 'https://open.canada.ca/data/dataset/009f9a49-c2d9-4d29-a6d4-1a228da335ce/resource/d3f883ce-4133-48da-bc76-c6b063d257a2/download/travelq-nil.csv', 'key': ['year', 'month'] },
            'hospitality-nil': { 'url' : 'https://open.canada.ca/data/dataset/b9f51ef4-4605-4ef2-8231-62a2edda1b54/resource/36a3b6cc-4f45-4081-8dbd-2340ca487041/download/hospitalityq-nil.csv', 'key': ['year', 'month'] },
            'briefingt-nil': { 'url' : 'https://open.canada.ca/data/dataset/ee9bd7e8-90a5-45db-9287-85c8cf3589b6/resource/5e28b544-720b-4745-9e55-3aac6464a4fb/download/briefingt-nil.csv', 'key': ['year', 'month'] },
            }

pco_orgs = [ 'pco-bcp', 'dpm-vpm', 'iga-aig', 'miga-maig', 'ghl-lgc', 'mdi-mid', 'ql-lq', 'srp-rsp' ]

def find_duplicates(url, key):
    response = requests.get(url).content
    data = pd.read_csv(io.StringIO(response.decode('utf-8')))
    pco_data = data[data['owner_org'].isin(pco_orgs)]
    sorted_pco_data = pco_data.sort_values(key)
    duplicates = sorted_pco_data[sorted_pco_data.duplicated(subset=key, keep=False)]
    return duplicates


with pd.ExcelWriter('pco-duplicates.xlsx') as writer:
    for idx, value in pd_list.items():
        print("Generating duplicate records using primary key '" + ' '.join([str(elem) for elem in value['key']]) + "' for " + idx)
        df = find_duplicates(value['url'], value['key'])
        df.to_excel(writer, sheet_name=idx)
