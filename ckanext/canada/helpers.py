import json
from pylons import c, config
from pylons.i18n import _
from ckan.model import User, Package
from wcms import wcms_dataset_comments, wcms_dataset_comment_count, wcms_dataset_rating
import datetime
import unicodedata

import ckanapi

import ckan.lib.helpers as h
from ckanext.scheming.helpers import scheming_get_preset
from ckan.logic.validators import boolean_validator

ORG_MAY_PUBLISH_OPTION = 'canada.publish_datasets_organization_name'
ORG_MAY_PUBLISH_DEFAULT_NAME = 'tb-ct'
PORTAL_URL_OPTION = 'canada.portal_url'
PORTAL_URL_DEFAULT = 'http://data.statcan.gc.ca'
SHOW_SITE_MSG_OPTION = 'canada.show_site_message'
SHOW_SITE_MSG_DEFAULT = 'False'
DATAPREVIEW_MAX = 500
FGP_URL_OPTION = 'fgp.ramp_base_url'
FGP_URL_DEFAULT = 'http://localhost/'


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
    fmt_choices = scheming_get_preset('canada_resource_format')['choices']
    resource_formats = set(r['format'] for r in pkg['resources'])
    for f in fmt_choices:
        if 'openness_score' not in f:
            continue
        if f['value'] not in resource_formats:
            continue
        resource_score = f.get('openness_score', 0)
        score = max(score, resource_score)

    for r in pkg['resources']:
        if 'data_includes_uris' in r.get('data_quality', []):
            score = max(4, score)
            if 'data_includes_links' in r.get('data_quality', []):
                score = max(5, score)
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

    return wcms_dataset_comments(pkg_id, lang)


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

    return wcms_dataset_rating(package_id)


def dataset_comment_count(package_id):

    return wcms_dataset_comment_count(package_id)


def portal_url():
    return str(config.get(PORTAL_URL_OPTION, PORTAL_URL_DEFAULT))

def is_site_message_showing():
    return str(config.get(SHOW_SITE_MSG_OPTION, SHOW_SITE_MSG_DEFAULT))
    
def googleanalytics_id():
    return str(config.get('googleanalytics.id'))
    
def drupal_session_present(request):
    for name in request.cookies.keys():
        if name.startswith("SESS"):
            return True
    
    return False
    
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
    portal_release_date = package.get('portal_release_date')
    ready_to_publish = package['ready_to_publish']

    if ready_to_publish == 'true' and not portal_release_date:
        return True
    else:
        return False

def get_datapreview_recombinant(resource_name, res_id):
    from ckanext.recombinant.tables import get_chromo
    t = get_chromo(resource_name)
    default_preview_args = {}
    if 'default_preview_sort' in t:
        default_preview_args['sort'] = t['default_preview_sort']

    lc = ckanapi.LocalCKAN(username=c.user)
    results = lc.action.datastore_search(
        resource_id=res_id, limit=0,
        **default_preview_args)

    lang = h.lang()
    field_label = {}
    for f in t['fields']:
        field_label[f['datastore_id']] = h._(f['label'])
    fields = [{
        'type': f['type'],
        'id': f['id'],
        'label': field_label.get(f['id'], f['id'])}
        for f in results['fields']]

    return h.snippet('package/wet_datatable.html',
        resource_id=res_id,
        ds_fields=fields)

def fgp_url():
    return str(config.get(FGP_URL_OPTION, FGP_URL_DEFAULT))

def contact_information(info):
    """
    produce label, value pairs from contact info
    """
    try:
        return json.loads(info)[h.lang()]
    except Exception:
        return {}

