# encoding: utf-8

"""Hello Analytics Reporting API V4."""

import argparse

from apiclient.discovery import build
import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools

import os
import gzip
import json
import urllib
import sys
import csv
import unicodecsv
import codecs
from collections import defaultdict

import ckanapi
import ckan
from ckanapi.errors import CKANAPIError
from ckan.logic import (NotAuthorized, NotFound)

import configparser
import psycopg2
import traceback

import openpyxl
import heapq

def write_xls(filename, sheets):
    #book = openpyxl.load_workbook('sheets.xlsx')
    book = openpyxl.Workbook()

    for sheet in sheets:
        ws = book.create_sheet(title=sheet.get('name', 'sheet 1'))
        for row in sheet.get('data',[]):
            ws.append(row)
        cols =  [col for col in ws.columns]
        widths = sheet.get('col_width', {})
        for k,v in widths.iteritems():
            ws.column_dimensions[cols[k][0].column].width = v
    try:
        sheet1 = book.get_sheet_by_name("Sheet")
        book.remove_sheet(sheet1)
    except:
        pass
    book.save(filename)

def write_csv(filename, rows, header=None):
    outf=open(filename, 'wb')
    outf.write(codecs.BOM_UTF8)
    writer = unicodecsv.writer(outf)

    if header:
        writer.writerow(header)
    for row in rows:
        writer.writerow(row)

proxy= os.environ['http_proxy']

# https://developers.google.com/analytics/devguides/reporting/core/v4/quickstart/installed-py
# https://developers.google.com/analytics/devguides/reporting/core/v4/basics
#CLIENT_SECRETS_PATH = 'client_secrets.json' # Path to client_secrets.json file.
#VIEW_ID = '<REPLACE_WITH_VIEW_ID>'


def initialize_analyticsreporting(client_secrets_path):
  """Initializes the analyticsreporting service object.

  Returns:
    analytics an authorized analyticsreporting service object.
  """
  SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
  DISCOVERY_URI = ('https://analyticsreporting.googleapis.com/$discovery/rest')

  # Parse command-line arguments.
  parser = argparse.ArgumentParser(
      formatter_class=argparse.RawDescriptionHelpFormatter,
      parents=[tools.argparser])
  # flags = parser.parse_args(['--noauth_local_webserver'])
  flags = parser.parse_args([])

  # Set up a Flow object to be used if we need to authenticate.
  flow = client.flow_from_clientsecrets(
      client_secrets_path, scope=SCOPES,
      message=tools.message_if_missing(client_secrets_path))

  # Prepare credentials, and authorize HTTP object with them.
  # If the credentials don't exist or are invalid run through the native client
  # flow. The Storage object will ensure that if successful the good
  # credentials will get written back to a file.
  storage = file.Storage('analyticsreporting.dat')
  credentials = storage.get()

  pi = httplib2.proxy_info_from_environment('http')
  if credentials is None or credentials.invalid:
    credentials = tools.run_flow(flow, storage, flags, http=httplib2.Http(proxy_info=pi))

  http = credentials.authorize(http=httplib2.Http(proxy_info=pi))

  # Build the service object.
  analytics = build('analytics', 'v4', http=http, discoveryServiceUrl=DISCOVERY_URI)

  return analytics

class DatasetDownload():
    def __init__(self, ga, view_id, conf_file):
        self.ga = ga
        self.view_id = view_id
        self.file = '/tmp/od-do-canada.jl.gz'
        self.site = ckanapi.RemoteCKAN('http://open.canada.ca/data')
        self.read_orgs()

        user, passwd, host, db = self.read_conf(conf_file)
        db = db.split('?')[0]
        try:
            self.conn = psycopg2.connect(
                database=db, user=user,
                password=passwd, host=host, port="5432")
        except:
            import traceback
            traceback.print_exce()
            print ("Opened database failed")
            sys.exit(-1)

    def read_conf(self,filename):
        config = configparser.ConfigParser()
        config.read(filename)
        psql_conn_str = config.get('app:main', 'sqlalchemy.url')
        import re
        r = re.match(r'^postgresql://(.*):(.*)@(.*)/(.*)', psql_conn_str)
        return (r.group(1), r.group(2), r.group(3), r.group(4))

    def get_deleted_dataset(self, id):
        cur = self.conn.cursor()
        cur.execute('''SELECT a.id, c.value, a.owner_org from package a,
                    package_extra c
                    where a.state='deleted' 
                        and a.id=c.package_id and c.key='title_translated'; ''')
        rows = cur.fetchall()
        for row in rows[:1]:
            id, title, org = row[0], row[1], row[2]
            return (title, org)

        return (None, None)

    def __delete__(self):
        if not self.file:
            if self.download_file:
                os.unlink(self.download_file)
                print('temp file deleted', self.download_file)

    def get_details(self, id):
        try:
            target_pkg = self.site.action.package_show(id=id)
        except:
            target_pkg = None
        return target_pkg

    def read_orgs(self):
        orgs = self.site.action.organization_list(all_fields=True)
        self.orgs = {}
        self.org_name2id = {}
        self.org_id2name = {}

        for rec in orgs:
            title = rec['title'].split('|')
            self.orgs[rec['id']] = title
            self.org_name2id[rec['name']] = rec['id']
            self.org_id2name[rec['id']] = [ rec['name'], rec['title'] ]
        assert(len(self.orgs)>100)
        print 'total orgs ', len(self.orgs)

    def read_portal(self, stats):
        self.ds = {}
        self.org_count = defaultdict(int)
        count = 0
        for records in self.download():
            count += len(records)
            print 'read records ', count, ' ',  len(self.ds)
            for rec in records:
                if not stats.get(rec['id']):
                    continue
                if self.og_type =='info':
                    if rec['type'] != 'info':
                        stats.pop(rec['id']) # not open info 
                        continue
                self.ds[rec['id']] = {'title_translated':rec['title_translated'],
                                      'owner_org':rec['owner_org']}
                self.org_count[rec['owner_org']] += 1
            
    def getStats(self, start_date, end_date, og_type):
        self.start_date = start_date
        self.end_date = end_date
        self.og_type = og_type

        start = '0'
        stats = defaultdict(int)
        while True:
            response = self.getRawReport(start)
            data, start = self.parseReport(response)
            for [url, count] in data:
                id = url.split('/')[-1]
                id = id.split('&')[0]
                id = id.strip()
                if len(id)!=36: continue #make sure it is an UUID
                stats[id] += int(count)
            if len(data)==0 or not start:
                print 'Done ', start, len(stats)
                break
            else:
                print start
        stats = dict(stats)
        self.read_portal(stats)

        if self.og_type == 'info':
            self.dump_info(stats)
        else:
            self.dump(stats)

    def dump_info(self, data):
        sheets =[]
        top100 = [[id,c] for id,c in data.iteritems()]
        top100 = heapq.nlargest(100, top100, key=lambda x:x[1])
        rows = [['ID / Identificateur',
                 'Title English / Titre en anglais',
                 'Title French / Titre en français', 
                 "Department Name English / Nom du ministère en anglais",
                 "Department Name French / Nom du ministère en français",
                 "number of downloads / nombre de téléchargements"]]
        for rec_id,count in top100:
            #get top20
            if len(rows)>=21:
                break
            rec = self.ds.get(rec_id, None)
            if not rec:
                #deleted, skip it
                continue
            else:
                rec_title = rec['title_translated']
                org_id = rec['owner_org']
            [_, org_title] = self.org_id2name.get(org_id)
            org_title = org_title.split('|')
            org_title = [x.strip() for x in org_title]
            rows.append( [rec_id, rec_title['en'], rec_title['fr'],
                          org_title[0], org_title[1], count])
        sheet1 = {'name':'Top 20 Datasets',
                  'data': rows,
                   'col_width':{0:40, 1:50, 2:50, 3:50, 4:50, 5:40}  # col:width
                   }
        sheets.insert(0, sheet1)
        write_xls('/tmp/downloads_info.xls', sheets)

    def dump(self, data):
        #further reduce to departments
        ds = defaultdict(int)
        sheets = defaultdict(list)
        deleted_ds = {}
        for id,c in data.iteritems():
            rec = self.ds.get(id, None)
            if not rec:
                print id, ' deleted'
                rec_title, org_id = self.get_deleted_dataset(id)
                deleted_ds[id] = {'title_translated':rec_title,
                                  'org_id':org_id}
                print (rec_title, org_id)
            else:
                org_id = rec['owner_org']
            ds[org_id] += c

            sheet = sheets[org_id]
            sheet.append(id)
            
        
        rows = []
        for k,v in ds.iteritems():
            title = self.orgs.get(k, ['', ''])
            if len(title) ==1:
                title.append(title[0])
            rows.append([title[0].strip(), title[1].strip(),v]) 
        rows.sort(key=lambda x: -x[2])
        header = ["Department Name English / Nom du ministère en anglais",
                  "Department Name French / Nom du ministère en français",
                  "number of downloads / nombre de téléchargements"]

        #write_csv('/tmp/a.csv', rows, header)
        
        #now save to xls
        self.saveXls(sheets, data, ds, deleted_ds)

    def saveXls(self, org_recs, data, org_stats, deleted_ds):
        sheets =[]
        rows =[]
        for k, [name, title] in self.org_id2name.iteritems():
            count = org_stats.get(k, 0)
            if count == 0:
                continue
            title = title.split('|')
            rows.append( [name, title[0].strip(), title[1].strip(), count])
        rows.sort(key=lambda x: -x[3])
        rows.insert(0, ['Abbreviation / Abréviation', 
                        "Department Name English / Nom du ministère en anglais",
                        "Department Name French / Nom du ministère en français",
                        "Number of downloads / Nombre de téléchargements"])
        sheet1 = {'name':'Summary by departments',
                  'data': rows,
                   'col_width':{0:26, 1:50, 2:50, 3:40}  # col:width
                   }

        #get top100
        top100 = [[id,c] for id,c in data.iteritems()]
        top100 = heapq.nlargest(100, top100, key=lambda x:x[1])
        rows = [['ID / Identificateur',
                 'Title English / Titre en anglais',
                 'Title French / Titre en français', 
                 "Department Name English / Nom du ministère en anglais",
                 "Department Name French / Nom du ministère en français",
                 "number of downloads / nombre de téléchargements"]]
        for rec_id,count in top100:
            rec = self.ds.get(rec_id, None)
            if not rec:
                rec_title = deleted_ds[rec_id]['title_translated']
                rec_title = json.loads(rec_title)
                org_id = deleted_ds[rec_id]['org_id']
            else:
                rec_title = rec['title_translated']
                org_id = rec['owner_org']
            [_, org_title] = self.org_id2name.get(org_id)
            org_title = org_title.split('|')
            org_title = [x.strip() for x in org_title]
            rows.append( [rec_id, rec_title['en'], rec_title['fr'],
                          org_title[0], org_title[1], count])
        sheet2 = {'name':'Top 100 Datasets',
                  'data': rows,
                   'col_width':{0:40, 1:50, 2:50, 3:50, 4:50, 5:40}  # col:width
                   }

        for org_id, recs in org_recs.iteritems():
            rows = []
            title = self.org_id2name.get(org_id, ['unknown'])[0]
            for rec_id in recs:
                rec = self.ds.get(rec_id, None)
                if not rec:
                    rec_title = deleted_ds[rec_id]['title_translated']
                    rec_title = json.loads(rec_title)
                else:
                    rec_title = rec['title_translated']
                count = data.get(rec_id)
                rows.append( [rec_id, rec_title['en'], rec_title['fr'], count])
            rows.sort(key=lambda x:-x[3])
            rows.insert(0, ['ID / Identificateur',
                            'Title English / Titre en anglais',
                            'Title French / Titre en français',
                            'Number of downloads / Nombre de téléchargements'])
            rows.append(['total','','', org_stats.get(org_id)])
            sheets.append({'name':title,
                           'data': rows,
                           'col_width':{0:40, 1:50, 2:50, 3:40}
                           }
                          )
        sheets.sort(key=lambda x: x['name'])
        sheets.insert(0, sheet2)
        sheets.insert(0, sheet1)
        write_xls('/tmp/downloads.xls', sheets)
        
    def getRawReport(self, start='0', size = '1000'):
          return self.ga.reports().batchGet(
              body={
                'reportRequests': [
                {
                  'viewId': self.view_id,
                  'dateRanges': [{'startDate': self.start_date, 'endDate': self.end_date}],
#                  'dateRanges': [{'startDate': '2017-06-01', 'endDate': '2017-06-30'}],
                  'metrics': [{'expression': 'ga:totalEvents'},
                              {'expression': 'ga:eventValue'},
                              {'expression': 'ga:uniqueEvents'} ],
                  'dimensions':[{'name':'ga:eventCategory'},
                                {'name':'ga:eventAction'},
                                {'name':'ga:pagePath'}
                                ],
                  'dimensionFilterClauses': [ {
                        'filters': [{
                            'dimensionName': 'ga:eventCategory',
                            'operator': "BEGINS_WITH",
                            'expressions': ['resource']
                            }]
                        }],
                  'orderBys':[
                    {'fieldName': 'ga:totalEvents',
                     'sortOrder': 'DESCENDING'
                    }],
                   'pageToken': start,
                   'pageSize': size,
                    
                }]
              }
          ).execute()

    def parseReport(self, response):
        for report in response.get('reports', []):
            columnHeader = report.get('columnHeader', {})
            dimensionHeaders = columnHeader.get('dimensions', [])
            metricHeaders = columnHeader.get('metricHeader', {}).get('metricHeaderEntries', [])
            
            id_idx = dimensionHeaders.index('ga:pagePath') # raise exception ValueError if not there
            
            metricHeaders = [ v['name'] for v in metricHeaders]
            count_idx = metricHeaders.index('ga:totalEvents') 
            rows = report.get('data', {}).get('rows', [])

            data = []
            for row in rows:
              dimensions = row.get('dimensions', [])
              dateRangeValues = row.get('metrics', [])
              data.append([dimensions[id_idx], dateRangeValues[0]['values'][count_idx]])
            return data, report.get('nextPageToken', None)

    def download(self):
        if not self.file:
            # dataset http://open.canada.ca/data/en/dataset/c4c5c7f1-bfa6-4ff6-b4a0-c164cb2060f7
            url='http://open.canada.ca/static/od-do-canada.jl.gz'
            r = requests.get(url, stream=True)

            f = tempfile.NamedTemporaryFile(delete=False)
            for chunk in r.iter_content(1024 * 64):
                    f.write(chunk)
            f.close()
            self.download_file = f.name

        records = []
        fname = self.file or f.name
        try:
            with gzip.open(fname, 'rb') as fd:
                for line in fd:
                    records.append(json.loads(line.decode('utf-8')))
                    if len(records) >= 500:
                        yield (records)
                        records = []
            if len(records) >0:
                yield (records)
                records = []
        except GeneratorExit:
            pass
        except:
            import traceback
            traceback.print_exc()
            print('error reading downloaded file')
            sys.exit(0)

def report(client_secret_path, view_id, og_config_file, start, end, og_type):
      analytics = initialize_analyticsreporting(client_secret_path)
      ds = DatasetDownload(analytics, view_id, og_config_file)
      ds.getStats(start, end, og_type)

def main():
    report(*sys.argv[1:])
      
if __name__ == '__main__':
  main()

