from pylons import c, config
from ckan.model import User, Package
import datetime
from sqlalchemy import select, bindparam, and_
from lxml.html.clean import clean_html
import plugins
import unicodedata

from ckanext.canada.metadata_schema import schema_description

ORG_MAY_PUBLISH_OPTION = 'canada.publish_datasets_organization_name'
ORG_MAY_PUBLISH_DEFAULT_NAME = 'tb-ct'
PORTAL_URL_OPTION = 'canada.portal_url'
PORTAL_URL_DEFAULT = 'http://data.statcan.gc.ca'


def may_publish_datasets(userobj=None):
    if not userobj:
        userobj = c.userobj
    if userobj.sysadmin:
        return True

    pub_org = config.get(ORG_MAY_PUBLISH_OPTION, ORG_MAY_PUBLISH_DEFAULT_NAME)
    for g in userobj.get_groups():
        if not g.is_organization:
            continue
        if g.name == pub_org:
            return True
    return False

def openness_score(pkg):
    score = 0
    fmt = schema_description.resource_field_by_id['format']['choices_by_key']
    for r in pkg['resources']:
        if r['resource_type'] != 'file':
            continue
        score = max(score, fmt[r['format']]['openness_score'])
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
def dataset_comments(pkg_id, lang):

    comment_list = []
    try:
        if (plugins.drupal_comments_table is not None):
            where_clause = []
            clause_1 = plugins.drupal_comments_table.c.pkg_id == bindparam('pkg_id')
            where_clause.append(clause_1)
            clause_2 = plugins.drupal_comments_table.c.language == bindparam('language')
            where_clause.append(clause_2)
            and_clause = and_(*where_clause)
            stmt = select([plugins.drupal_comments_table], and_clause)

            for comment in stmt.execute(pkg_id=pkg_id, language=lang):
                 comment_body = clean_html(comment[3])
                 comment_list.append({'date': comment[0], 'thread': comment[2], 'comment_body': comment_body, 'user': comment[1]})


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


def dataset_rating(package_id):

    rating = None
    try:

        if plugins.drupal_ratings_table is not None:
            stmt = select([plugins.drupal_ratings_table], whereclause=plugins.drupal_ratings_table.c.pkg_id==bindparam('pkg_id'))
            row = stmt.execute(pkg_id=package_id).fetchone()
            if row:
                rating = row[0]

    except KeyError:
        pass
    return int(0 if rating is None else rating)

def dataset_comment_count(package_id):

    count = 0

    try:

        if plugins.drupal_comments_count_table is not None:
            stmt = select([plugins.drupal_comments_count_table], whereclause=plugins.drupal_comments_count_table.c.pkg_id==bindparam('pkg_id'))
            row = stmt.execute(pkg_id=package_id).fetchone()
            if row:
                count = row[0]
       
    except KeyError:
       pass
    return count


def portal_url():
    return str(config.get(PORTAL_URL_OPTION, PORTAL_URL_DEFAULT))
    
def googleanalytics_id():
    return str(config.get('googleanalytics.id'))
    
def parse_release_date_facet(facet_results):
    counts = facet_results['counts'][1::2]
    ranges = facet_results['counts'][0::2]
    facet_dict = dict()
    
    if len(counts) == 0:
        return dict()
    elif len(counts) == 1:
        if ranges[0] == facet_results['start']:
            facet_dict = {'published': {'count': counts[0], 'url_param': '[' + ranges[0] + ' TO ' + facet_results['end'] + ']'} }
        else:
            facet_dict = {'scheduled': {'count': counts[0], 'url_param': '[' + ranges[0] + ' TO ' + facet_results['end'] + ']'} }
    else:
        facet_dict = {'published': {'count': counts[0], 'url_param': '[' + ranges[0] + ' TO ' + ranges[1] + ']'} , 
                      'scheduled': {'count': counts[1], 'url_param': '[' + ranges[1] + ' TO ' + facet_results['end'] + ']'} }
    
    return facet_dict
    
def is_ready_to_publish(package):
    portal_release_date = None
    for e in package['extras']:
        if e['key'] == 'ready_to_publish':
            ready_to_publish = e['value']
            continue
        elif e['key'] == 'portal_release_date':
            portal_release_date = e['value']
            continue
            
    #if datetime.datetime.strptime(portal_release_date, "%Y-%m-%d %H:%M:%S") < datetime.datetime.now():
    
    if ready_to_publish == 'true' and not portal_release_date:
        return True
    else:
        return False