import json
import re
from pylons import c, config
from pylons.i18n import _
from ckan.model import User, Package, Activity
import ckan.model as model
import wcms
import datetime
import unicodedata
import ckan as ckan
import jinja2

import ckanapi

from ckantoolkit import h
import ckan.lib.helpers as hlp
import ckan.plugins.toolkit as t
from ckanext.scheming.helpers import scheming_get_preset
from ckan.logic.validators import boolean_validator
import webhelpers.html as html
from webhelpers.html.tags import link_to
import dateutil.parser
import geomet.wkt as wkt
import json as json

ORG_MAY_PUBLISH_OPTION = 'canada.publish_datasets_organization_name'
ORG_MAY_PUBLISH_DEFAULT_NAME = 'tb-ct'
PORTAL_URL_OPTION = 'canada.portal_url'
PORTAL_URL_DEFAULT_EN = 'https://open.canada.ca'
PORTAL_URL_DEFAULT_FR = 'https://ouvert.canada.ca'
DATAPREVIEW_MAX = 500
FGP_URL_OPTION = 'fgp.service_endpoint'
FGP_URL_DEFAULT = 'http://localhost/'
GRAVATAR_SHOW_OPTION = 'ckan.gravatar_show'
GRAVATAR_SHOW_DEFAULT = True
WET_URL = config.get('wet_boew.url', '')
WET_JQUERY_OFFLINE_OPTION = 'wet_boew.jquery.offline'
WET_JQUERY_OFFLINE_DEFAULT = False
GEO_MAP_TYPE_OPTION = 'wet_theme.geo_map_type'
GEO_MAP_TYPE_DEFAULT = 'static'



def get_translated_t(data_dict, field):
    '''
    customized version of core get_translated helper that also looks
    for machine translated values (e.g. en-t-fr and fr-t-en)

    Returns translated_text, is_machine_translated (True/False)
    '''

    language = h.lang()
    try:
        return data_dict[field+'_translated'][language], False
    except KeyError:
        if field+'_translated' in data_dict:
            for l in data_dict[field+'_translated']:
                if l.startswith(language + '-t-'):
                    return data_dict[field+'_translated'][l], True
        val = data_dict.get(field, '')
        return (_(val) if val and isinstance(val, basestring) else val), False


def language_text_t(text, prefer_lang=None):
    '''
    customized version of scheming_language_text helper that also looks
    for machine translated values (e.g. en-t-fr and fr-t-en)

    Returns translated_text, is_machine_translated (True/False)
    '''
    if not text:
        return u'', False

    assert text != {}
    if hasattr(text, 'get'):
        try:
            if prefer_lang is None:
                prefer_lang = h.lang()
        except TypeError:
            pass  # lang() call will fail when no user language available
        else:
            try:
                return text[prefer_lang], False
            except KeyError:
                for l in text:
                    if l.startswith(prefer_lang + '-t-'):
                        return text[l], True
                pass

        default_locale = config.get('ckan.locale_default', 'en')
        try:
            return text[default_locale], False
        except KeyError:
            pass

        l, v = sorted(text.items())[0]
        return v, False

    t = gettext(text)
    if isinstance(t, str):
        return t.decode('utf-8'), False
    return t, False


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


def user_organizations(user):
    u = User.get(user['name'])
    return u.get_groups(group_type = "organization")

def catalogue_last_update_date():
    return '' # FIXME: cache this value or add an index to the DB for query below
    q = model.Session.query(Activity.timestamp).filter(
        Activity.activity_type.endswith('package')).order_by(
        Activity.timestamp.desc()).first()
    return q[0].replace(microsecond=0).isoformat() if q else ''

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

def get_license(license_id):
    return Package.get_license_register().get(license_id)


def normalize_strip_accents(s):
    """
    utility function to help with sorting our French strings
    """
    if isinstance(s, str):
        return s
    if not s:
        s = u''
    s = unicodedata.normalize('NFD', s)
    return s.encode('ascii', 'ignore').decode('ascii').lower()


def portal_url():
    url = PORTAL_URL_DEFAULT_FR if h.lang() == 'fr' else PORTAL_URL_DEFAULT_EN
    return str(config.get(PORTAL_URL_OPTION, url))


def googleanalytics_id():
    return str(config.get('googleanalytics.id'))

def adobe_analytics_login_required(current_url):
    return "2" #return 1 if page requires a login and 2 if page is public

def adobe_analytics_lang():
    if h.lang() == 'en':
        return 'eng'
    elif h.lang() == 'fr':
        return 'fra'

def adobe_analytics_js():
    return str(config.get('adobe_analytics.js', ''))
    
def loop11_key():
    return str(config.get('loop11.key', ''))

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

    priority = len(chromo['datastore_primary_key'])
    pk_priority = 0
    fields = []
    for f in chromo['fields']:
        out = {
            'type': f['datastore_type'],
            'id': f['datastore_id'],
            'label': h.recombinant_language_text(f['label'])}
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


def show_openinfo_facets():
    '''
    Return True when the open information facets are active
    '''
    for f in h.get_facet_items_dict('collection'):
        if f['name'] == 'publication' and f['active']:
            return True
    for f in h.get_facet_items_dict('portal_type'):
        if f['name'] == 'info':
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
        if displayname==config.get('ckan.site_id', '').strip():
            displayname = _('A system administrator')

        if maxlength and len(user.display_name) > maxlength:
            displayname = displayname[:maxlength] + '...'

        return h.literal(h.link_to(
                displayname,
                h.url_for(controller='user', action='read', id=name)
            )
        )
# FIXME: because ckan/lib/activity_streams is terrible
h.linked_user = linked_user


def link_to_user(user, maxlength=0):
    """ Return the HTML snippet that returns a link to a user.  """

    # Do not link to pseudo accounts
    if user in [model.PSEUDO_USER__LOGGED_IN, model.PSEUDO_USER__VISITOR]:
        return user
    if not isinstance(user, model.User):
        user_name = unicode(user)
        user = model.User.get(user_name)
        if not user:
            return user_name

    if user:
        _name = user.name if model.User.VALID_NAME.match(user.name) else user.id
        displayname = user.display_name
        if maxlength and len(user.display_name) > maxlength:
            displayname = displayname[:maxlength] + '...'
        return html.tags.link_to(displayname,
                       h.url_for(controller='user', action='read', id=_name))

def gravatar_show():
    return t.asbool(config.get(GRAVATAR_SHOW_OPTION, GRAVATAR_SHOW_DEFAULT))

def get_datapreview(res_id):

    #import pdb; pdb.set_trace()
    dsq_results = ckan.logic.get_action('datastore_search')({}, {'resource_id': res_id, 'limit' : 100})
    return h.snippet('package/wet_datatable.html', ds_fields=dsq_results['fields'], ds_records=dsq_results['records'])

def iso_to_goctime(isodatestr):
    dateobj = dateutil.parser.parse(isodatestr)
    return dateobj.strftime('%Y-%m-%d')

def geojson_to_wkt(gjson_str):
    ## Ths GeoJSON string should look something like:
    ##  u'{"type": "Polygon", "coordinates": [[[-54, 46], [-54, 47], [-52, 47], [-52, 46], [-54, 46]]]}']
    ## Convert this JSON into an object, and load it into a Shapely object. The Shapely library can
    ## then output the geometry in Well-Known-Text format

    try:
        gjson = json.loads(gjson_str)
        try:
            gjson = _add_extra_longitude_points(gjson)
        except:
            # this is bad, but all we're trying to do is improve
            # certain shapes and if that fails showing the original
            # is good enough
            pass
        shape = gjson
    except ValueError:
        return None # avoid 500 error on bad geojson in DB

    wkt_str = wkt.dumps(shape)
    return wkt_str


def url_for_wet_theme(*args):
    file = args[0] or ''
    return h.url_for_wet(file, theme=True)

def url_for_wet(*args, **kw):
    file = args[0] or ''
    theme = kw.get('theme', False)

    if not WET_URL:
        return h.url_for_static_or_external(
            ('GCWeb' if theme else 'wet-boew') + file
        )

    return WET_URL + '/' + ('GCWeb' if theme else 'wet-boew') + file


def wet_jquery_offline():
    return t.asbool(config.get(WET_JQUERY_OFFLINE_OPTION, WET_JQUERY_OFFLINE_DEFAULT))


def get_map_type():
    return str(config.get(GEO_MAP_TYPE_OPTION, GEO_MAP_TYPE_DEFAULT))


def _add_extra_longitude_points(gjson):
    """
    Assume that sides of a polygon with the same latitude should
    be rendered as curves following that latitude instead of
    straight lines on the final map projection
    """
    import math
    fuzz = 0.00001
    if gjson[u'type'] != u'Polygon':
        return gjson
    coords = gjson[u'coordinates'][0]
    plng, plat = coords[0]
    out = [[plng, plat]]
    for lng, lat in coords[1:]:
        if plat - fuzz < lat < plat + fuzz:
            parts = int(abs(lng-plng))
            if parts > 300:
                # something wrong with the data, give up
                return gjson
            for i in range(parts)[1:]:
                out.append([(i*lng + (parts-i)*plng)/parts, lat])
        out.append([lng, lat])
        plng, plat = lng, lat
    return {u'coordinates': [out], u'type': u'Polygon'}


def recombinant_description_to_markup(text):
    """
    Return text as HTML escaped strings joined with '<br/>, links enabled'
    """
    # very lax, this is trusted text defined in a schema not user-provided
    url_pattern = r'(https?:[^)\s"]{20,})'
    markup = []
    for i, part in enumerate(re.split(url_pattern, h.recombinant_language_text(text))):
        if i % 2:
            markup.append(jinja2.Markup('<a href="{0}">{1}</a>'.format(part, jinja2.escape(part))))
        else:
            markup.extend(jinja2.Markup('<br/>'.join(
               jinja2.escape(t) for t in part.split('\n')
            )))
    # extra dict because language text expected and language text helper
    # will cause plain markup to be escaped
    return {'en': jinja2.Markup(''.join(markup))}
