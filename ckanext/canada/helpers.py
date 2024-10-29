import json
import re
import inspect
from ckan.plugins.toolkit import config, _, h, g, request
from ckan.model import User, Package
from ckanext.activity.model import Activity
import ckan.model as model
import datetime
import unicodedata
import ckan as ckan
import html
from six import text_type
from bs4 import BeautifulSoup
from ckan import plugins

from ckanapi import NotFound
from ckantoolkit import aslist
import ckan.plugins.toolkit as t
from ckanext.scheming.helpers import scheming_get_preset
import html
import dateutil.parser
import geomet.wkt as wkt
import json as json
from markupsafe import Markup, escape
from ckan.lib.helpers import core_helper
from ckan.plugins.core import plugin_loaded
from ckan.logic import NotAuthorized
import ckan.lib.datapreview as datapreview

from ckanext.security.cache.login import max_login_attempts

try:
    from ckanext.xloader.utils import XLoaderFormats
except ImportError:
    XLoaderFormats = None

ORG_MAY_PUBLISH_OPTION = 'canada.publish_datasets_organization_name'
ORG_MAY_PUBLISH_DEFAULT_NAME = 'tb-ct'
PORTAL_URL_OPTION = 'canada.portal_url'
PORTAL_URL_DEFAULT_EN = 'https://open.canada.ca'
PORTAL_URL_DEFAULT_FR = 'https://ouvert.canada.ca'
DATAPREVIEW_MAX = 500
CDTS_VERSION = config.get('ckanext.canada.cdts_version', 'v5_0_1')
CDTS_URI = 'https://www.canada.ca/etc/designs/canada/cdts/gcweb'
GEO_MAP_TYPE_OPTION = 'wet_theme.geo_map_type'
GEO_MAP_TYPE_DEFAULT = 'static'
RELEASE_DATE_FACET_STEP = 100


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
        return (_(val) if val and isinstance(val, str) else val), False


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

    t = _(text)
    if isinstance(t, str):
        return t.decode('utf-8'), False
    return t, False


def may_publish_datasets(userobj=None):
    if not userobj:
        userobj = g.userobj
    if userobj.sysadmin:
        return True

    pub_org = config.get(ORG_MAY_PUBLISH_OPTION, ORG_MAY_PUBLISH_DEFAULT_NAME)
    for group in userobj.get_groups():
        if not group.is_organization:
            continue
        if group.name == pub_org:
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

# copied from ckan 2.6 branch
# https://github.com/open-data/ckan/blob/ee0a94c97f8988e78c9b1f92f92adb5c26884841/ckan/lib/helpers.py#L1245
def canada_date_str_to_datetime(date_str):
    '''Convert ISO-like formatted datestring to datetime object.
    This function converts ISO format date- and datetime-strings into
    datetime objects.  Times may be specified down to the microsecond.  UTC
    offset or timezone information may **not** be included in the string.
    Note - Although originally documented as parsing ISO date(-times), this
           function doesn't fully adhere to the format.  This function will
           throw a ValueError if the string contains UTC offset information.
           So in that sense, it is less liberal than ISO format.  On the
           other hand, it is more liberal of the accepted delimiters between
           the values in the string.  Also, it allows microsecond precision,
           despite that not being part of the ISO format.
    '''

    time_tuple = re.split('[^\d]+', date_str, maxsplit=5)

    # Extract seconds and microseconds
    if len(time_tuple) >= 6:
        m = re.match('(?P<seconds>\d{2})(\.(?P<microseconds>\d+))?$',
                     time_tuple[5])
        if not m:
            raise ValueError('Unable to parse %s as seconds.microseconds' %
                             time_tuple[5])
        seconds = int(m.groupdict().get('seconds'))
        microseconds = int((str(m.groupdict(0).get('microseconds')) + '00000')[0:6])
        time_tuple = time_tuple[:5] + [seconds, microseconds]

    return datetime.datetime(*map(int, time_tuple))

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

def adv_search_url():
    return config.get('ckanext.canada.adv_search_url_fr') if h.lang() == 'fr' else config.get('ckanext.canada.adv_search_url_en')

def adv_search_mlt_root():
    return "{0}/donneesouvertes/similaire/".format(config.get('ckanext.canada.adv_search_url_fr')) if h.lang() == 'fr' else "{0}/opendata/similar/".format(config.get('ckanext.canada.adv_search_url_en'))


def ga4_id():
    return str(config.get('ga4.id'))

def adobe_analytics_login_required(current_url):
    # type: (str) -> int
    """
    1: login required
    2: public
    3: intranet or extranet

    Only supporting Public Portal w/ Adobe Analytics for now,
    so just always return 2 for public.
    """
    return 2

def adobe_analytics_lang():
    # type: () -> str
    """
    Return Adobe Analytics expected language codes.

    Returns `eng` (English) by default
    """
    if h.lang() == 'fr':
        return 'fra'
    return 'eng'

def adobe_analytics_js():
    """
    Return partial Adobe Analytics JS address.

    Exclude `//assets.adobedtm.com/` prefix and `.js` suffix.

    See: https://github.com/wet-boew/cdts-sgdc/blob/v4.1.0/src/gcweb/refTop.ejs
    """
    return str(config.get('ckanext.canada.adobe_analytics.js', ''))


def adobe_analytics_creator(organization=None, package=None):
    # type: (dict|None, dict|None) -> str
    """
    Generates HTML Meta Tag for Adobe Analytics, along with extra GoC
    page ownership HTML attribute.

    Need to have organization and package parameters separately for Organization/Group templates.

    creator and owner_1 should be the Organization who made the "page" (org, package, resource, or PD record set)
    owner_2, owner_3, and owner_4 are for the org_section field in the package schema.
    """
    # defaults
    creator = _('Treasury Board of Canada Secretariat')
    owner_1 = _('Treasury Board of Canada Secretariat')
    owner_2 = 'N/A'
    owner_3 = 'N/A'
    owner_4 = 'N/A'

    # set creator and owner_1 to the package's organization title (language respective)
    if organization:
        if ' | ' in organization.get('title'):
            creator = organization.get('title').split(' | ')[1 if h.lang() == 'fr' else 0].strip()
        else:
            creator = h.get_translated(organization, h.lang()).strip()
        owner_1 = creator

    # set owners 2-4 to the package's org_section field value if available (language respective)
    if package and 'org_section' in package and h.scheming_language_text(package.get('org_section')):
        org_sections = h.scheming_language_text(package.get('org_section')).split(',')
        osl = len(org_sections)
        owner_2 = org_sections[0].strip() if osl >= 1 else 'N/A'
        owner_3 = org_sections[1].strip() if osl >= 2 else 'N/A'
        owner_4 = org_sections[2].strip() if osl >= 3 else 'N/A'

    return Markup(u'<meta property="dcterms:creator" content="%s" ' \
            'data-gc-analytics-owner="%s|%s|%s|%s"/>' % (
                html.escape(creator), html.escape(owner_1),
                html.escape(owner_2), html.escape(owner_3),
                html.escape(owner_4)))


def resource_view_meta_title(package, resource, view, is_subtitle=False):
    # type: (dict, dict, dict, bool) -> str
    """
    Generates the string for the title meta tag for Resource Views.

    Includes the Resource View translated title.
    """
    package_title = h.get_translated(package, 'title')
    resource_title = h.get_translated(resource, 'name')
    view_title = view['title_fr'] if h.lang() == 'fr' else view['title']
    if not is_subtitle:
        return u'%s - %s - %s - %s' % (
            html.escape(package_title), html.escape(resource_title),
            html.escape(view_title), html.escape(_(g.site_title)))
    return Markup(u'%s - %s - %s' % (
        html.escape(package_title), html.escape(resource_title),
        html.escape(view_title)))


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


def release_date_facet_start_year():
    today = int(datetime.datetime.now(EST()).strftime("%Y"))
    return today - RELEASE_DATE_FACET_STEP


def is_ready_to_publish(package):
    portal_release_date = package.get('portal_release_date')
    ready_to_publish = package.get('ready_to_publish')

    if ready_to_publish == 'true' and not portal_release_date:
        return True
    else:
        return False

def get_datapreview_recombinant(resource_name, resource_id, owner_org, dataset_type):
    from ckanext.recombinant.tables import get_chromo
    chromo = get_chromo(resource_name)
    default_preview_args = {}
    priority = len(chromo['datastore_primary_key'])
    pk_priority = 0
    fields = []
    fids = []
    for f in chromo['fields']:
        if f.get('published_resource_computed_field'):
            continue
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
        fids.append(f['datastore_id'])

    pkids = [fids.index(k) for k in aslist(chromo['datastore_primary_key'])]
    return h.snippet('package/wet_datatable.html',
        resource_name=resource_name,
        resource_id=resource_id,
        owner_org=owner_org,
        primary_keys=pkids,
        dataset_type=dataset_type,
        ds_fields=fields)

def contact_information(info):
    """
    produce label, value pairs from contact info
    """
    try:
        return json.loads(info)[h.lang()]
    except Exception:
        return {}


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


def cdts_asset(file_path, theme=True):
    return CDTS_URI + '/' + CDTS_VERSION + ('/wet-boew' if theme else '/cdts') + file_path


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
            markup.append(Markup('<a href="{0}">{1}</a>'.format(part, escape(part))))
        else:
            markup.extend(Markup('<br/>'.join(
               escape(t) for t in part.split('\n')
            )))
    # extra dict because language text expected and language text helper
    # will cause plain markup to be escaped
    return {'en': Markup(''.join(markup))}


def mail_to_with_params(email_address, name, subject, body):
    email = escape(email_address)
    author = escape(name)
    mail_subject = escape(subject)
    mail_body = escape(body)
    html = Markup(u'<a href="mailto:{0}?subject={2}&body={3}">{1}</a>'.format(email, author, mail_subject, mail_body))
    return html

def get_timeout_length():
    return int(config.get('beaker.session.timeout', 0))


def canada_search_domain():
    if 'staging' in config.get('ckan.site_url', ''):
        return _('search-staging.open.canada.ca')
    return _('search.open.canada.ca')


def canada_check_access(package_id):
    try:
        return h.check_access('package_update', {'id': package_id})
    except NotFound:
        return False


def get_user_email(user_id):
    '''
    Return user email address if belong to the same organization
    '''
    u = User.get(user_id)
    orgs = h.organizations_available()
    org_ids = [o['id'] for o in orgs]

    if not u.is_in_groups(org_ids):
        return ""

    context = {'model': model,
               'session': model.Session,
               'keep_email': True}

    try:
        data_dict = {'id': user_id}
        user_dict = ckan.logic.get_action('user_show')(context, data_dict)

        return user_dict['email']

    except NotFound as e:
        return ""


core_helper(plugin_loaded)


def organization_member_count(id):
    try:
        members = ckan.logic.get_action(u'member_list')({}, {
            u'id': id,
            u'object_type': u'user',
            u'include_total': True,
        })
    except NotFound:
        raise NotFound( _('Members not found'))
    except NotAuthorized:
        return -1

    return len(members)


def _build_flash_html_for_ga4(message, category, caller, allow_html=True):
    """
    All flash messages will be given an event name and action attribute.

    data-ga-event: CALLER in format of <module>.<class>.<method> | <module>.<method>
    data-ga-action: CATEGORY in format of notice | error | success
    """
    return '<div class="canada-ga-flash" data-ga-event="%s" data-ga-action="%s">%s</div>' \
        % (caller, category, escape(message) if not allow_html else Markup(message))


def _get_caller_info(stack):
    parentframe = stack[1][0]
    module_info = inspect.getmodule(parentframe)

    # module name
    if module_info:
        caller_module = module_info.__name__

    # class name
    caller_class = None
    if 'self' in parentframe.f_locals:
        caller_class = parentframe.f_locals['self'].__class__.__name__

    # method name
    caller_method = None
    if parentframe.f_code.co_name != '<module>':
        caller_method = parentframe.f_code.co_name

    # Remove reference to frame
    # See: https://docs.python.org/3/library/inspect.html#the-interpreter-stack
    del parentframe

    if caller_class:
        return '%s.%s.%s' % (caller_module, caller_class, caller_method)

    return '%s.%s' % (caller_module, caller_method)


def flash_notice(message, allow_html=True):
    """
    Show a flash message of type notice

    Adding the view/action caller for GA4 Custom Events
    """
    t.h.flash(_build_flash_html_for_ga4(message, 'notice',
                                        _get_caller_info(inspect.stack()),
                                        allow_html=allow_html),
              category='alert-info')


def flash_error(message, allow_html=True):
    """
    Show a flash message of type error

    Adding the view/action caller for GA4 Custom Events
    """
    t.h.flash(_build_flash_html_for_ga4(message, 'error',
                                        _get_caller_info(inspect.stack()),
                                        allow_html=allow_html),
              category='alert-danger')


def flash_success(message, allow_html=True):
    """
    Show a flash message of type success

    Adding the view/action caller for GA4 Custom Events
    """
    t.h.flash(_build_flash_html_for_ga4(message, 'success',
                                        _get_caller_info(inspect.stack()),
                                        allow_html=allow_html),
              category='alert-success')


def get_loader_status_badge(resource):
    # type: (dict) -> str
    """
    Displays a custom badge for the status of Xloader and DataStore
    for the specified resource.
    """
    if not t.asbool(config.get('ckanext.canada.show_loader_badges', False)):
        return ''

    if not XLoaderFormats:
        return ''

    if not resource.get('url_type') == 'upload' or \
    not XLoaderFormats.is_it_an_xloader_format(resource.get('format')):
        # we only want to show badges for uploads of supported xloader formats
        return ''

    is_datastore_active = resource.get('datastore_active', False)

    try:
        xloader_job = t.get_action("xloader_status")(None, {"resource_id": resource.get('id')})
    except (t.ObjectNotFound, t.NotAuthorized):
        xloader_job = {}

    if xloader_job.get('status') == 'complete':
        # the xloader task is complete, show datastore active or inactive.
        # xloader will delete the datastore table at the beggining of the job run.
        # so this will only be true if the job is fully finished.
        status = 'active' if is_datastore_active else 'inactive'
    elif xloader_job.get('status') in ['pending', 'running', 'running_but_viewable', 'error']:
        # the job is running or pending or errored
        # show the xloader status
        status = xloader_job.get('status')
        if status == 'running_but_viewable':
            # treat running_but_viewable the same as running
            status = 'running'
    else:
        # we do not know what the status is
        status = 'unknown'

    messages = {
        'pending': _('Data awaiting load to DataStore'),
        'running': _('Loading data into DataStore'),
        'complete': _('Data loaded into DataStore'),
        'error': _('Failed to load data into DataStore'),
        'active': _('Data available in DataStore'),
        'inactive': _('Resource not active in DataStore'),
        'unknown': _('DataStore status unknown'),
    }

    pusher_url = t.h.url_for('xloader.resource_data',
                             id=resource.get('package_id'),
                             resource_id=resource.get('id'))

    badge_url = t.h.url_for_static('/static/img/badges/{lang}/datastore-{status}.svg'.format(lang=t.h.lang(), status=status))

    title = t.h.render_datetime(xloader_job.get('last_updated'), with_hours=True) \
        if xloader_job.get('last_updated') else ''

    return Markup(u'<a href="{pusher_url}" class="loader-badge"><img src="{badge_url}" alt="{alt}" title="{title}"/></a>'.format(
        pusher_url=pusher_url,
        badge_url=badge_url,
        alt=html.escape(messages[status], quote=True),
        title=html.escape(title, quote=True)))


def get_resource_view(resource_view_id):
    """
    Returns a resource view dict for the resource_view_id
    """
    try:
        return t.get_action('resource_view_show')(
            {}, {'id': resource_view_id})
    except t.ObjectNotFound:
        return None


def resource_view_type(resource_view):
    view_plugin = datapreview.get_view_plugin(resource_view['view_type'])
    return view_plugin.info().get('title')


def fgp_viewer_url(package):
    """
    Returns a link to fgp viewer for the package
    """
    viewers = package.get('display_flags', [])
    if 'fgp_viewer' in viewers:
        if h.lang() == 'fr':
            openmap_uri = 'carteouverte'
        else:
            openmap_uri = 'openmap'

        return h.adv_search_url() + '/' + openmap_uri + '/' + package.get('id')


def date_field(field, pkg):
    if pkg.get(field) and ' ' in pkg.get(field):
        return pkg.get(field).split(' ')[0]
    return pkg.get(field, None)


def split_piped_bilingual_field(field_text, client_lang):
    if field_text is not None and ' | ' in field_text:
        return field_text.split(' | ')[1 if client_lang == 'fr' else 0]
    return field_text


def search_filter_pill_link_label(search_field, search_extras):
    links_labels = []

    if search_field == 'portal_type':

        # Custom dataset type labels (suggested datasets discontinued - 2024-05-09)
        preset_choices = [{'value': 'dataset', 'label': _('Open Data')},
                          {'value': 'info', 'label': _('Open Information')},]

        # Add PD types
        for pd_type in h.recombinant_get_types():
            preset_choices.append({'value': pd_type, 'label': _(h.recombinant_get_chromo(pd_type).get('title'))})

    elif search_field == 'status':

        preset_choices = [{'value': 'department_contacted',
                           'label': _('Request sent to data owner - awaiting response')}]

    elif search_field == 'ready_to_publish':

        preset_choices = [{'value': 'true', 'label': _('Pending')},
                          {'value': 'false', 'label': _('Draft')},]

    else:

        preset_choices = (h.scheming_get_preset('canada_' + search_field) or {}).get('choices', [])

        if search_field == 'collection':

            collection_choices = preset_choices
            preset_choices = [{'value': 'pd', 'label': _('Proactive Publication')}]

            for collection_type in collection_choices:
                preset_choices.append(collection_type)

            # Add PD types
            for pd_type in h.recombinant_get_types():
                preset_choices.append({'value': pd_type, 'label': _(h.recombinant_get_chromo(pd_type).get('title'))})

    def remove_filter_button_link_label(_field, _value, s_extras, _choices):

        extrs = s_extras.copy() if s_extras else {}
        extrs.update(request.view_args)
        link = h.remove_url_param(_field, value=_value, extras=extrs)
        label = _value

        if _field == 'organization':
            org = h.get_organization(_value)
            if org:
                label = split_piped_bilingual_field(org.get('title'), h.lang())
        elif _field == 'portal_release_date':
            if _value.startswith('[%s' % release_date_facet_start_year()):
                label = _('Published')
            else:
                label = _('Scheduled')
        else:
            label = h.scheming_language_text(h.list_dict_filter(_choices, 'value', 'label', _value))

        return link, label

    for value in g.fields_grouped[search_field]:
        if not isinstance(value, text_type):
            for v in value:
                links_labels.append(remove_filter_button_link_label(_field=search_field,
                                                                    _value=v,
                                                                    s_extras=search_extras,
                                                                    _choices=preset_choices))
        else:
            links_labels.append(remove_filter_button_link_label(_field=search_field,
                                                                _value=value,
                                                                s_extras=search_extras,
                                                                _choices=preset_choices))

    return links_labels


def ckan_to_cdts_breadcrumbs(breadcrumb_content):
    """
    The Wet Builder requires a list of JSON objects.

    There is no good way to get the breadcrumbs from the CKAN template blocks
    into parsed JSON objects. We need to use an HTML Parser to do it.

    See: https://cdts.service.canada.ca/app/cls/WET/gcweb/v4_1_0/cdts/samples/breadcrumbs-en.html
    """
    breadcrumb_html = BeautifulSoup(breadcrumb_content, 'html.parser')
    cdts_breadcrumbs = []
    if g.is_registry:
        cdts_breadcrumbs.append({
            'title': _('Registry Home'),
            'href': '/%s' % h.lang(),
        })
    else:
        cdts_breadcrumbs.extend([{
            'title': _('Open Government'),
            'href': '/%s' % h.lang(),
        },{
            'title': _('Search'),
            'href': adv_search_url(),
        }])

    for breadcrumb in breadcrumb_html.find_all('li'):
        anchor = breadcrumb.find('a')
        link = {
            'title': breadcrumb.text if not anchor else anchor.text,
            'href': '' if not anchor else anchor['href'],
        }
        if anchor and anchor.get('title'):
            link['acronym'] = anchor.get('title')

        if g.is_registry:
            cdts_breadcrumbs.append(link)
        elif 'active' not in breadcrumb.get('class', []):
            cdts_breadcrumbs.append(link)

    return cdts_breadcrumbs


def validation_status(resource_id):
    try:
        validation = t.get_action('resource_validation_show')(
            {'ignore_auth': True},
            {'resource_id': resource_id})
        return validation.get('status')
    except (t.ObjectNotFound, KeyError):
        return 'unknown'


def is_user_locked(user_name):
    """
    Returns whether the user is locked out of their account or not.
    """
    try:
        throttle = t.get_action('security_throttle_user_show')({'user': g.user}, {'user': user_name})
    except (NotAuthorized, KeyError):
        return None

    if throttle and 'count' in throttle and throttle['count'] >= max_login_attempts():
        return True

    return False


def available_purge_types():
    """
    Returns a list of available purge types.
    """
    types = []
    for plugin in plugins.PluginImplementations(plugins.IDatasetForm):
        for package_type in plugin.package_types():
            if package_type not in types:
                types.append(package_type)
    for plugin in plugins.PluginImplementations(plugins.IGroupForm):
        for group_types in plugin.group_types():
            if group_types not in types:
                types.append(group_types)
    return types
