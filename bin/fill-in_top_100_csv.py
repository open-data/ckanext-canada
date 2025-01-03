
import argparse
from ckanapi import RemoteCKAN, NotFound
from configparser import ConfigParser
import unicodecsv


argparser = argparse.ArgumentParser(
    description='Populate the top 100 datasets csv with dataset and organization name'
)
argparser.add_argument('-f', '--file', action='store',
                       default='', dest='csvfile',
                       help='Empty CSV file from TBS')
argparser.add_argument('-c', '--config', action='store',
                       default='development.ini',
                       dest='configfile',
                       help='Config file')
argparser.add_argument('-o', '--outfile', action='store',
                       default='output.csv', dest='outfile',
                       help='CSV file to write out to')
argparser.add_argument('-l', '--lang', action='store',
                       default='en', dest='lang',
                       help='language [en|fr]')
args = argparser.parse_args()


def main():
    ini_config = ConfigParser()
    ini_config.read(args.configfile)
    remote_ckan_url = ini_config.get('ckan', 'ckan.url')
    remote_apikey = ini_config.get('ckan', 'ckan.apikey')
    # Create CKAN API connector to the portal
    ckan_portal = RemoteCKAN(remote_ckan_url, apikey=remote_apikey)

    fi = open(args.csvfile, 'r')
    fo = open(args.outfile, 'w')

    csv_in = unicodecsv.reader(fi, encoding='utf-8')
    csv_out = unicodecsv.writer(fo, encoding='utf-8')
    csv_out.writerow(csv_in.next())
    for row in csv_in:
        # Look up the package in CKAN
        try:
            pkg = ckan_portal.action.package_show(id=row[0])
            # If the record does not exist, then a NotFound exception will be thrown
            row[2] = pkg['org_title_at_publication'][args.lang]
            row[1] = pkg['title_translated'][args.lang]
            csv_out.writerow(row)
        except NotFound:
            pass


main()
