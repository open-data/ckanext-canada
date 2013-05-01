from pylons import c
import ckan.model as model
import datetime
import psycopg2 as pg2
from ckan.lib.cli import parse_db_config

ORG_MAY_PUBLISH_KEY = 'publish'
ORG_MAY_PUBLISH_VALUE = 'True'

def may_publish_datasets():
    if c.userobj.sysadmin:
        return True

    for g in c.userobj.get_groups():
        if not g.is_organization:
            continue
        if g.extras.get(ORG_MAY_PUBLISH_KEY) == ORG_MAY_PUBLISH_VALUE:
            return True


def user_organizations(user):
    u = model.User.get(user['name'])
    return u.get_groups(group_type = "organization")
    
def today():
    return datetime.datetime.now(EST()).strftime("%Y-%m-%d")
    
# Return the Date format that the WET datepicker requires to function properly
def date_format(date_string):
    if not date_string:
        return None
    else:
        return datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
    
class EST(datetime.tzinfo):
    def utcoffset(self, dt):
      return datetime.timedelta(hours=-5)

    def dst(self, dt):
        return datetime.timedelta(0)
  
# Retrieve the comments for this dataset that have been saved in the Drupal database
# This is ugly - look away!  Or better yet, suggest improvements
def dataset_comments(pkg_id):

    #import pdb; pdb.set_trace()
    dbd = parse_db_config('ckan.drupal.url')
    drupal_conn_string = "host='%s' dbname='%s' user='%s' password='%s'" % (dbd['db_host'], dbd['db_name'], dbd['db_user'], dbd['db_pass'])    
    
    drupal_conn = pg2.connect(drupal_conn_string)
    drupal_cursor = drupal_conn.cursor()
    
    drupal_cursor.execute(
       """select c.subject, c.changed, c.name, c.thread, f.comment_body_value 
          from comment c inner join field_data_comment_body f on c.cid = f.entity_id 
          inner join od_package o on o.pkg_node_id = c.nid 
          where o.pkg_id = %s""", (pkg_id,))
    
    comment_list = []
    for comment in drupal_cursor:
       comment_list.append({'subject': comment[0], 'date': comment[1], 'thread': comment[2], 'comment_body': comment[3]})
       
    return comment_list
