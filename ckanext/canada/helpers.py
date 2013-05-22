from pylons import c, config
from ckan.model import User, Package
import datetime
import psycopg2 as pg2
from lxml.html.clean import clean_html
from ckan.lib.cli import parse_db_config
import unicodedata

ORG_MAY_PUBLISH_OPTION = 'publish_datasets_organization_name'
ORG_MAY_PUBLISH_DEFAULT_NAME = 'tb-ct'

def may_publish_datasets():
    if c.userobj.sysadmin:
        return True

    pub_org = config.get(ORG_MAY_PUBLISH_OPTION, ORG_MAY_PUBLISH_DEFAULT_NAME)
    for g in c.userobj.get_groups():
        if not g.is_organization:
            continue
        if g.name == pub_org:
            return True
    return False

def openness_score(pkg):
    score = 0
    for r in pkg['resources']:
        # scores copied from ckanext-qa and our valid formats
        score = max(score, {
            'CSV': 3,
            'JSON': 3,
            'kml / kmz': 3,
            'ods': 2,
            'RDF': 4,
            'rdfa': 4,
            'TXT': 1,
            'xls': 2,
            'xlsm': 2,
            'XML': 3,
            }.get(r['format'], 1))
    return score


def user_organizations(user):
    u = User.get(user['name'])
    return u.get_groups(group_type = "organization")
    
def today():
    return datetime.datetime.now(EST()).strftime("%Y-%m-%d")
    
# Return the Date format that the WET datepicker requires to function properly
def date_format(date_string):
    if not date_string:
        return None
    try:
        return datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S"
            ).strftime("%Y-%m-%d")
    except ValueError:
        return date_string

class EST(datetime.tzinfo):
    def utcoffset(self, dt):
      return datetime.timedelta(hours=-5)

    def dst(self, dt):
        return datetime.timedelta(0)
        
def remove_duplicates(a_list):
    s = set()
    for i in a_list:
        s.add(i)
            
    return s


# Retrieve the comments for this dataset that have been saved in the Drupal database
# This is ugly - look away!  Or better yet, suggest improvements
def dataset_comments(pkg_id):

    #import pdb; pdb.set_trace()
    comment_list = []
    try:
      dbd = parse_db_config('ckan.drupal.url')
      if (dbd):
        drupal_conn_string = "host='%s' dbname='%s' user='%s' password='%s'" % (dbd['db_host'], dbd['db_name'], dbd['db_user'], dbd['db_pass'])    
        
        drupal_conn = pg2.connect(drupal_conn_string)
        drupal_cursor = drupal_conn.cursor()
        
        # add this to the SQL statement to limit comments to those that are published  'and status = 0'
        drupal_cursor.execute(
           """select c.subject, to_char(to_timestamp(c.changed), 'YYYY-MM-DD'), c.name, c.thread, f.comment_body_value from comment c 
inner join field_data_comment_body f on c.cid = f.entity_id
inner join opendata_package o on o.pkg_node_id = c.nid
where o.pkg_id = %s""", (pkg_id,))
      
    
        for comment in drupal_cursor:
           comment_body = clean_html(comment[4])
           comment_list.append({'subject': comment[0], 'date': comment[1], 'thread': comment[3], 'comment_body': comment_body, 'user': comment[2]})

    except KeyError:
       pass
    return comment_list


def get_license(license_id):
    return Package.get_license_register().get(license_id)


def normalize_strip_accents(s):
    """
    utility function to help with sorting our French strings
    """
    if not s:
        s = u''
    s = unicodedata.normalize('NFD', s)
    return s.encode('ascii', 'ignore').decode('ascii').lower()


