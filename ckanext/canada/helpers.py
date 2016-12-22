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
from ckan.logic import get_action
from ckan.lib.base import model

from sqlalchemy.sql import select

import ckan.logic as ckan_logic
import ckan.plugins as p
import ckan.lib.plugins as lib_plugins
import ckan.lib.dictization.model_dictize as dictize
from ckan.lib.navl.dictization_functions import Missing

ORG_MAY_PUBLISH_OPTION = 'canada.publish_datasets_organization_name'
ORG_MAY_PUBLISH_DEFAULT_NAME = 'tb-ct'
PORTAL_URL_OPTION = 'canada.portal_url'
PORTAL_URL_DEFAULT = 'http://data.statcan.gc.ca'
DATAPREVIEW_MAX = 500
FGP_URL_OPTION = 'fgp.ramp_base_url'
FGP_URL_DEFAULT = 'http://localhost/'

def group_or_org_plugin_dictize(context, group_dict, include_followers, is_org):
    plugins = p
    if is_org:
        plugin_type = plugins.IOrganizationController
    else:
        plugin_type = plugins.IGroupController

    for item in plugins.PluginImplementations(plugin_type):
        item.read(group)

    group_plugin = lib_plugins.lookup_group_plugin(group_dict['type'])
    try:
        schema = group_plugin.db_to_form_schema_options({
            'type': 'show',
            'api': 'api_version' in context,
            'context': context})
    except AttributeError:
        schema = group_plugin.db_to_form_schema()

    if include_followers:
        model = context['model']
        group_dict['num_followers'] = logic.get_action('group_follower_count')(
            {'model': model, 'session': model.Session},
            {'id': group_dict['id']})
    else:
        group_dict['num_followers'] = 0
    if not group_dict.get('display_name'):
        group_dict['display_name'] = None
    if not group_dict.get('package_count'):
        group_dict['package_count'] = None

    schema = ckan_logic.schema.default_show_group_schema()
    group_dict, errors = lib_plugins.plugin_validate(
        group_plugin, context, group_dict, schema,
        'organization_show' if is_org else 'group_show')
    return group_dict


def _query_organization_extras(context, data_dict):
    model = context['model']
    group = model.group_table
    is_latest_revision = not(context.get('revision_id') or
                         context.get('revision_date'))
    execute = dictize._execute if is_latest_revision else dictize._execute_with_revision

    # customize: owner org extras
    extra = model.group_extra_table
    q = select([extra]).where(extra.c.group_id == data_dict["id"])
    result = execute(q, group, context)
    org_extras = dictize.extras_list_dictize(result, context)
    data_dict["extras"] = org_extras
    data_dict = group_or_org_plugin_dictize(context, data_dict, False, True)
    return data_dict

# overwrite
def organizations_available(permission='edit_group'):
    '''Return a list of organizations that the current user has the specified
    permission for.
    '''
    context = {'user': c.user}
    data_dict = {'permission': permission}
    results = get_action('organization_list_for_user')(context, data_dict)
    organization_results = []
    for org in results:
        organization_results.append(_query_organization_extras(context, org))
    return organization_results

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
    score = 1
    fmt_choices = scheming_get_preset('canada_resource_format')['choices']
    resource_formats = set(r['format'] for r in pkg['resources'])
    for f in fmt_choices:
        if 'openness_score' not in f:
            continue
        if f['value'] not in resource_formats:
            continue
        score = max(score, f['openness_score'])

    for r in pkg['resources']:
        if 'data_includes_uris' in r.get('data_quality', []):
            score = max(4, score)
            if 'data_includes_links' in r.get('data_quality', []):
                score = max(5, score)
    return score

def get_organization(name):
    context = {'model': model}
    data_dict = {'name': name,
        "include_extra": True,
        'all_fields': True}
    organization = get_action('organization_show')(context, data_dict)
    return organization

def user_organizations(user):
    u = User.get(user['name'])
    groups = u.get_groups(group_type="organization")
    groups_data = []
    for group in groups:
        context = {'model': model}
        data_dict = {'id': group.id,
                    "include_extra": True,
                    'all_fields': True}
        group_dict = get_action('organization_show')(context, data_dict)
        groups_data.append(group_dict)
    return groups_data

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
    chromo = get_chromo(resource_name)
    default_preview_args = {}

    lc = ckanapi.LocalCKAN(username=c.user)
    results = lc.action.datastore_search(
        resource_id=res_id,
        limit=0,
        )

    priority = len(chromo['datastore_primary_key'])
    pk_priority = 0
    fields = []
    for f in chromo['fields']:
        out = {
            'type': f['datastore_type'],
            'id': f['datastore_id'],
            'label': h._(f['label'])}
        if out['id'] in chromo['datastore_primary_key']:
            out['priority'] = pk_priority
            pk_priority += 1
        else:
            out['priority'] = priority
            priority += 1
        fields.append(out)

    return h.snippet('package/wet_datatable.html',
        resource_name=resource_name,
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

def show_subject_facet():
    '''
    Return True when the subject facet should be visible
    '''
    if any(f['active'] for f in h.get_facet_items_dict('subject')):
        return True
    return not show_fgp_facets()

def show_fgp_facets():
    '''
    Return True when the fgp facets and map cart should be visible
    '''
    for group in [
            'topic_category', 'spatial_representation_type', 'fgp_viewer']:
        if any(f['active'] for f in h.get_facet_items_dict(group)):
            return True
    for f in h.get_facet_items_dict('collection'):
        if f['name'] == 'fgp':
            return f['active']
    return False


def json_loads(value):
    return json.loads(value)


# FIXME: terrible hacks
def gravatar(*args, **kwargs):
    '''Brute force disable gravatar'''
    return ''
def linked_gravatar(*args, **kwargs):
    '''Brute force disable gravatar'''
    return ''

# FIXME: terrible, terrible hacks
def linked_user(user, maxlength=0, avatar=20):
    '''Brute force disable gravatar, mostly copied from ckan/lib/helpers'''
    from ckan import model
    if not isinstance(user, model.User):
        user_name = unicode(user)
        user = model.User.get(user_name)
        if not user:
            return user_name
    if user:
        name = user.name if model.User.VALID_NAME.match(user.name) else user.id
        displayname = user.display_name

        if maxlength and len(user.display_name) > maxlength:
            displayname = displayname[:maxlength] + '...'

        return h.literal(h.link_to(
                displayname,
                h.url_for(controller='user', action='read', id=name)
            )
        )
# FIXME: because ckan/lib/activity_streams is terrible
h.linked_user = linked_user
h.organizations_available = organizations_available
