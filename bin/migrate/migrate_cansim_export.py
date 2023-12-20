#!/usr/bin/env python
from datetime import datetime
import simplejson
import sys

# Quick script to transform the CANSIM and Summary Table JSON data from CKAN 2.0 to 2.3
#  -  Replace subject UUID with the list
#  -  Add a portal_release_date field
#  -  Change ready_to_publish value from 1 to "true"
#  -  Change "catalog_type": "Data | Donn\u00e9es" to "type": "dataset"
#
# The script reads from stdin and prints the modified stirng to stdout

subject_replacements = {
    '86EB6B9F-344C-4C3E-982D-53164994516A': ["arts_music_literature"],
    '04D07B59-8D90-455C-9C84-7C1DF833473B': ["agriculture"],
    '3AC17C98-F356-4CC8-BAEB-886037E5C2EE': ["economics_and_industry"],
    '0AA56AD7-4CB3-4F7E-A741-9503231BC697': ["education_and_training"],
    '1BEB670E-8A73-4217-BCD2-6189F92053E2': ["government_and_politics"],
    '7D5846DC-74D0-415A-A853-318DCD89E731': ["health_and_safety"],
    '704B3281-511F-4FFB-85C7-D437892CECE2': ["history_and_archaeology"],
    '70B236D3-B7CE-443C-89C2-FEE7277F41C9': ["information_and_communications"],
    'F97F8830-B980-4A20-9B13-D572F1C094F0': ["labour"],
    '43BB3E2A-DA38-4005-9A57-8CBEB60F5FE0': ["language_and_linguistics"],
    'BBBDFE5C-9EC2-4393-A801-5866D176CF08': ["law"],
    '8ACBA39A-BD70-4113-98F8-8A8A11E095C1': ["military"],
    '9E3985CD-58EC-4DBA-AF73-5711AF379DE4': ["nature_and_environment"],
    'BEF4D60C-E2D1-46B9-96C0-B55902F076F1': ["persons"],
    'D1EFA3C1-FC9D-4E53-9BD4-90434626D213': ["processes"],
    '8C3A29E9-292D-47E3-8163-51FF8AB4E6D3': ["society_and_culture"],
    'FB6B00F0-6271-42D6-ACB7-FFE664843698': ["science_and_technology"],
    '949D4BF7-0AF0-49BD-8C76-AF0B82E72CC2': ["transport"]
}

freq_dict={
    "Annually | Annuel": "P1Y",
    "As Needed | Au besoin": "as_needed",
    "Quarterly | Trimestriel": "P3M",
    "Monthly | Mensuel": "P1M",
}

lang_dict={
    "eng; CAN | fra; CAN": ['en', 'fr'],
    "fra; CAN": ['fr'],
    "eng; CAN": ['en'],
}


def main():
    try:
        release_date = datetime.now().strftime("%Y-%m-%d")
        try:
            for line in sys.stdin:
                rec = simplejson.loads(line)
                rec = rec.get('record', rec)
                rec["portal_release_date"] = release_date
                if not rec.get('date_published'):
                    rec['date_published'] = release_date

                rec["ready_to_publish"] = "true"
                rec["imso_approval"] = "true"
                if "catalog_type" in rec:
                    del rec["catalog_type"]
                rec["type"] = "dataset"
                if "subject" in rec:
                    if rec["subject"] in subject_replacements:
                        rec["subject"] = subject_replacements[rec["subject"]]
                    else:
                        print >> sys.stderr, 'Invalid subject "{0}" for {1}'.format(rec["subject"], rec["id"])
                        continue
                rec['author_email'] = 'statcan.infostats-infostats.statcan@canada.ca'
                rec['maintainer_email'] = 'statcan.infostats-infostats.statcan@canada.ca'

                url_en, url_fr = rec.pop('url', None), rec.pop('url_fra', None)
                rec['program_url'] = {'en':url_en, 'fr':url_fr}

                notes_en = rec.pop('notes','')
                notes_fr = rec.pop('notes_fra','')
                rec['notes_translated'] = {'en':notes_en, 'fr':notes_fr}

                data_series_name_en = rec.pop('data_series_name', '')
                data_series_name_fr = rec.pop('data_series_name_fra', '')
                rec['data_series_name'] = {'en':data_series_name_en, 'fr':data_series_name_en}

                title_en = rec.get('title', '')
                title_fr = rec.pop('title_fra', '')
                rec['title_translated']={'en':title_en, 'fr':title_fr}

                data_series_issue_identification = rec.pop("data_series_issue_identification", "")
                data_series_issue_identification_fra = rec.pop("data_series_issue_identification_fra", "")
                rec["data_series_issue_identification"]={
                        'en':data_series_issue_identification,
                        'fr':data_series_issue_identification_fra
                }

                freq = rec.pop('maintenance_and_update_frequency', '')
                if freq:
                    rec['frequency'] = freq_dict.get(freq, 'as_needed')

                keywords = rec.pop('keywords','')
                keywords_fr = rec.pop('keywords_fra','')
                rec['keywords'] = {'en':[keywords], 'fr':[keywords_fr]}

                rec['collection'] = 'primary'
                rec['jurisdiction'] = 'federal'
                rec['geographic_region']= []
                rec['restrictions'] = 'unrestricted'

                for res in rec['resources']:
                    name = res.pop('name','')
                    name_fr = res.pop('name_fra','')
                    res['name_translated'] = {'en':name, 'fr':name_fr}
                    lang = res.pop('language', '')
                    res['language'] = lang_dict.get(lang, [])

                    rformat = res.get('format', '')
                    if rformat =='HTML':
                        res['resource_type']='guide'
                    else:
                        res['resource_type']='dataset'

                print(simplejson.dumps(rec))

        except IOError:
            print >> sys.stderr, 'Error while reading line.'

    except KeyError:
        if 'warehouse' in sys.argv:
            sys.exit(85)
        else:
            raise
main()
