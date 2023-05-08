#!/usr/bin/env python
# coding=utf-8

"""
Script that scrapes CONTACT_NAME from Departmental Audit Committee
Members Appointed and Non-Appointed dataset. The dataset is available on the
Open Government Portal:
https://open.canada.ca/data/en/dataset/1f681b53-bba4-437b-96b0-78af262e0ff8

USAGE: python download_dac.py -o/--output outfile.yaml

"""

import codecs
import getopt
import json
import yaml
import sys
import ssl
from urllib import urlopen


def main(argv):
    try:
        outfile = ''
        verify = True
        opts, args = getopt.getopt(argv, "o: v:", ["output=", "verify="])
        for opt, arg in opts:
            if opt in ("-o", "--output"):
                outfile = arg
            if opt in ("-v", "--verify"):
                verify = True if arg == "1" else False
        if not outfile:
            raise ValueError

    except (ValueError, getopt.GetoptError):
        print("USAGE: python download_dac.py -o/--output outfile.yaml [-v/--verify 1|0]")
        sys.exit(1)

    # Extract member names from API endpoint and publish as yaml
    output = codecs.open(outfile, 'w', encoding='utf-8')
    output.write('# Departmental Audit Committee member names to be used in '
                 'dropdown on recombinant templates\n\n')

    url = 'https://open.canada.ca/data/api/3/action/datastore_search_sql?sql' \
          '=SELECT distinct "CONTACT_NAME" from ' \
          '"59c86d81-fd29-495f-9a7a-7ba3d2c70cc2" '
    context = ssl.create_default_context()
    if verify is False:
        print("Ignoring ssl verification...")
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    response = urlopen(url, context=context)
    results = json.loads(response.read().decode('utf-8'))
    records = sorted(results['result']['records'],
                     key=lambda k: k['CONTACT_NAME'].lower())
    for record in records:
        contact = {record['CONTACT_NAME']: record['CONTACT_NAME']}
        output.write(yaml.safe_dump(contact, encoding='utf-8', allow_unicode=True).decode('utf-8'))
    output.close()


if __name__ == "__main__":
    main(sys.argv[1:])
