from typing import Optional, Union, Any, Tuple, List, Set, Dict, cast
from ckan.types import Context

import json
import re
import inspect
from urllib.parse import urlsplit
from ckan.plugins.toolkit import (
    config,
    asbool,
    aslist,
    get_action,
    _,
    h,
    g,
    request,
    ObjectNotFound,
    NotAuthorized
)
from ckan.model import User, Package
from ckanext.activity.model import Activity
import ckan.model as model
from ckan.model.license import License
import datetime
import unicodedata
import html
from six import text_type
from bs4 import BeautifulSoup
from ckan import plugins

from ckanext.scheming.helpers import scheming_get_preset
import dateutil.parser
import geomet.wkt as wkt
from markupsafe import Markup, escape
from ckan.lib.helpers import core_helper
from ckan.plugins.core import plugin_loaded
import ckan.lib.datapreview as datapreview

from ckanext.recombinant.tables import get_chromo
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


def get_translated_t(data_dict: Dict[str, Any],
                     field: str) -> Tuple[str, bool]:
    '''
    customized version of core get_translated helper that also looks
    for machine translated values (e.g. en-t-fr and fr-t-en)

    Returns translated_text, is_machine_translated (True/False)
    '''

    language = h.lang()
    try:
        return data_dict[field + '_translated'][language], False
    except KeyError:
        if field+'_translated' in data_dict:
            for trans_field in data_dict[field + '_translated']:
                if trans_field.startswith(language + '-t-'):
                    return data_dict[field + '_translated'][trans_field], True
        val = data_dict.get(field, '')
        return (_(val) if val and isinstance(val, str) else val), False


# FIXME: this is only for fluent tags...try to fix??
def language_text_t(text: Union[Dict[str, Any], str],
                    prefer_lang: Optional[str] = None) -> \
                        Tuple[Optional[str], bool]:
    '''
    customized version of scheming_language_text helper that also looks
    for machine translated values (e.g. en-t-fr and fr-t-en)

    Returns translated_text, is_machine_translated (True/False)
    '''
    if not text:
        return '', False

    assert text != {}
    if hasattr(text, 'get'):
        try:
            if prefer_lang is None:
                prefer_lang = h.lang()
        except TypeError:
            pass  # lang() call will fail when no user language available
        else:
            try:
                # type_ignore_reason: incomplete typing
                return text[prefer_lang], False  # type: ignore
            except KeyError:
                if prefer_lang:
                    for line in text:
                        if line.startswith(prefer_lang + '-t-'):
                            # type_ignore_reason: incomplete typing
                            return text[line], True  # type: ignore
                pass

        default_locale = config.get('ckan.locale_default', 'en')
        try:
            return text[default_locale], False
        except KeyError:
            pass

        # type_ignore_reason: incomplete typing
        _l, v = sorted(text.items())[0]  # type: ignore
        return v, False

    t = _(text)
    if isinstance(t, bytes):
        return t.decode('utf-8'), False
    return t, False


def may_publish_datasets(userobj: Optional['model.User'] = None) -> bool:
    if not userobj:
        userobj = g.userobj

    if not userobj:
        return False

    if userobj.sysadmin:
        return True

    pub_org = config.get(ORG_MAY_PUBLISH_OPTION, ORG_MAY_PUBLISH_DEFAULT_NAME)
    for group in userobj.get_groups():
        if not group.is_organization:
            continue
        if group.name == pub_org:
            return True

    return False


def openness_score(pkg: Dict[str, Any]) -> int:
    score = 1
    field_preset = scheming_get_preset('canada_resource_format')
    fmt_choices = []
    if field_preset:
        fmt_choices = field_preset['choices']
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


def user_organizations(user: Dict[str, Any]) -> List[Union['model.Group', Any]]:
    u = User.get(user['name'])
    if not u:
        return []
    return u.get_groups(group_type="organization")


def catalogue_last_update_date() -> str:
    return ''  # FIXME: cache this value or add an index to the DB for query below
    q = model.Session.query(Activity.timestamp).filter(
        Activity.activity_type.endswith('package')).order_by(
        Activity.timestamp.desc()).first()
    return q[0].replace(microsecond=0).isoformat() if q else ''


def today() -> str:
    return datetime.datetime.now(EST()).strftime("%Y-%m-%d")


# Return the Date format that the WET datepicker requires to function properly
def date_format(date_string: Optional[str]) -> Optional[str]:
    if not date_string:
        return None
    try:
        return datetime.datetime.strptime(
            date_string, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
    except ValueError:
        return date_string


class EST(datetime.tzinfo):
    def utcoffset(self, dt: 'datetime.datetime') -> 'datetime.timedelta':
        return datetime.timedelta(hours=-5)

    def dst(self, dt: 'datetime.datetime') -> 'datetime.timedelta':
        return datetime.timedelta(0)


# copied from ckan 2.6 branch
# https://github.com/open-data/ckan
# /blob/ee0a94c97f8988e78c9b1f92f92adb5c26884841/ckan/lib/helpers.py#L1245
def canada_date_str_to_datetime(date_str: str) -> 'datetime.datetime':
    '''
    Convert ISO-like formatted datestring to datetime object.

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

    time_tuple = re.split(r'[^\d]+', date_str, maxsplit=5)

    # Extract seconds and microseconds
    if len(time_tuple) >= 6:
        m = re.match(r'(?P<seconds>\d{2})(\.(?P<microseconds>\d+))?$',
                     time_tuple[5])
        if not m:
            raise ValueError('Unable to parse %s as seconds.microseconds' %
                             time_tuple[5])
        seconds = int(m.groupdict()['seconds'])
        microseconds = int((str(m.groupdict(0).get('microseconds')) + '00000')[0:6])
        time_tuple = time_tuple[:5] + [seconds, microseconds]

    # type_ignore_reason: typchecker can't guess number of arguments
    return datetime.datetime(*map(int, time_tuple))  # type: ignore


def remove_duplicates(a_list: List[Any]) -> Set[Any]:
    s = set()
    for i in a_list:
        s.add(i)

    return s


def get_license(license_id: str) -> License:
    return Package.get_license_register().get(license_id)


def normalize_strip_accents(s: Union[str, bytes]) -> str:
    """
    Utility function to help with sorting our French strings
    """
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    if not s:
        s = ''
    s = unicodedata.normalize('NFD', s)
    return s.encode('ascii', 'ignore').decode('ascii').lower()


def portal_url() -> str:
    url = PORTAL_URL_DEFAULT_FR if h.lang() == 'fr' else PORTAL_URL_DEFAULT_EN
    return str(config.get(PORTAL_URL_OPTION, url))


def adv_search_url() -> str:
    return config.get('ckanext.canada.adv_search_url_fr') if \
        h.lang() == 'fr' else config.get('ckanext.canada.adv_search_url_en')


def adv_search_mlt_root() -> str:
    return "{0}/donneesouvertes/similaire/".format(
        config.get('ckanext.canada.adv_search_url_fr')) if \
            h.lang() == 'fr' else "{0}/opendata/similar/".format(
                config.get('ckanext.canada.adv_search_url_en'))


def ga4_id() -> str:
    return str(config.get('ga4.id'))


def adobe_analytics_login_required(current_url: str) -> int:
    """
    1: login required
    2: public
    3: intranet or extranet

    Only supporting Public Portal w/ Adobe Analytics for now,
    so just always return 2 for public.
    """
    return 2


def adobe_analytics_lang() -> str:
    """
    Return Adobe Analytics expected language codes.

    Returns `eng` (English) by default
    """
    if h.lang() == 'fr':
        return 'fra'
    return 'eng'


def adobe_analytics_js() -> str:
    """
    Return partial Adobe Analytics JS address.

    Exclude `//assets.adobedtm.com/` prefix and `.js` suffix.

    See: https://github.com/wet-boew/cdts-sgdc/blob/v4.1.0/src/gcweb/refTop.ejs
    """
    return str(config.get('ckanext.canada.adobe_analytics.js', ''))


def adobe_analytics_creator(organization: Optional[Dict[str, Any]] = None,
                            package: Optional[Dict[str, Any]] = None) -> \
                                Markup:
    """
    Generates HTML Meta Tag for Adobe Analytics, along with extra GoC
    page ownership HTML attribute.

    Need to have organization and package parameters
    separately for Organization/Group templates.

    creator and owner_1 should be the Organization who made
    the "page" (org, package, resource, or PD record set)
    owner_2, owner_3, and owner_4 are for the org_section
    field in the package schema.
    """
    # defaults
    creator = _('Treasury Board of Canada Secretariat')
    owner_1 = _('Treasury Board of Canada Secretariat')
    owner_2 = 'N/A'
    owner_3 = 'N/A'
    owner_4 = 'N/A'

    # set creator and owner_1 to the package's
    # organization title (language respective)
    if organization:
        org_title = organization.get('title')
        if org_title and ' | ' in org_title:
            creator = org_title.split(' | ')[
                1 if h.lang() == 'fr' else 0].strip()
        else:
            creator = h.get_translated(organization, h.lang()).strip()
        owner_1 = creator

    # set owners 2-4 to the package's org_section
    # field value if available (language respective)
    if (
      package and 'org_section' in package and
      h.scheming_language_text(package.get('org_section'))):
        org_sections = h.scheming_language_text(
            package.get('org_section')).split(',')
        osl = len(org_sections)
        owner_2 = org_sections[0].strip() if osl >= 1 else 'N/A'
        owner_3 = org_sections[1].strip() if osl >= 2 else 'N/A'
        owner_4 = org_sections[2].strip() if osl >= 3 else 'N/A'

    return Markup('<meta property="dcterms:creator" content="%s" '
                  'data-gc-analytics-owner="%s|%s|%s|%s"/>' % (
                    html.escape(creator), html.escape(owner_1),
                    html.escape(owner_2), html.escape(owner_3),
                    html.escape(owner_4)))


def resource_view_meta_title(package: Dict[str, Any],
                             resource: Dict[str, Any],
                             view: Dict[str, Any],
                             is_subtitle: Optional[bool] = False) -> \
                                Union[Markup, str]:
    """
    Generates the string for the title meta tag for Resource Views.

    Includes the Resource View translated title.
    """
    package_title = h.get_translated(package, 'title')
    resource_title = h.get_translated(resource, 'name')
    view_title = view['title_fr'] if h.lang() == 'fr' else view['title']
    if not is_subtitle:
        return '%s - %s - %s - %s' % (
            html.escape(package_title), html.escape(resource_title),
            html.escape(view_title), html.escape(_(g.site_title)))
    return Markup('%s - %s - %s' % (
        html.escape(package_title), html.escape(resource_title),
        html.escape(view_title)))


def loop11_key() -> str:
    return str(config.get('loop11.key', ''))


def parse_release_date_facet(facet_results: Dict[str, Any]) -> Dict[str, Any]:
    counts = facet_results['counts'][1::2]
    ranges = facet_results['counts'][0::2]
    facet_dict = dict()

    if len(counts) == 0:
        return dict()
    elif len(counts) == 1:
        if ranges[0] == facet_results['start']:
            facet_dict = {
                'published': {
                    'count': counts[0],
                    'url_param': '[' + ranges[0] + ' TO ' + facet_results['end'] + ']'}
            }
        else:
            facet_dict = {
                'scheduled': {
                    'count': counts[0],
                    'url_param': '[' + ranges[0] + ' TO ' + facet_results['end'] + ']'}
            }
    else:
        facet_dict = {
            'published': {
                'count': counts[0],
                'url_param': '[' + ranges[0] + ' TO ' + ranges[1] + ']'},
            'scheduled': {
                'count': counts[1],
                'url_param': '[' + ranges[1] + ' TO ' + facet_results['end'] + ']'}
        }

    return facet_dict


def release_date_facet_start_year() -> int:
    today = int(datetime.datetime.now(EST()).strftime("%Y"))
    return today - RELEASE_DATE_FACET_STEP


def is_ready_to_publish(package: Dict[str, Any]) -> bool:
    portal_release_date = package.get('portal_release_date')
    ready_to_publish = package.get('ready_to_publish')

    if ready_to_publish == 'true' and not portal_release_date:
        return True
    else:
        return False


def get_datapreview_recombinant(resource_name: str,
                                resource_id: str,
                                owner_org: str,
                                dataset_type: str) -> str:
    chromo = get_chromo(resource_name)
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


def contact_information(info: str) -> Dict[str, Any]:
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


def json_loads(value: str) -> Dict[str, Any]:
    try:
        return json.loads(value)
    except Exception:
        return {}


def get_datapreview(res_id: str) -> str:
    dsq_results = get_action('datastore_search')(
        cast(Context, {}), {'resource_id': res_id, 'limit': 100})
    return h.snippet('package/wet_datatable.html',
                     ds_fields=dsq_results['fields'],
                     ds_records=dsq_results['records'])


def iso_to_goctime(isodatestr: str) -> str:
    dateobj = dateutil.parser.parse(isodatestr)
    return dateobj.strftime('%Y-%m-%d')


def geojson_to_wkt(gjson_str: str) -> Any:
    # Ths GeoJSON string should look something like:
    #  '{"type": "Polygon",
    #    "coordinates": [[[-54, 46], [-54, 47], [-52, 47], [-52, 46], [-54, 46]]]}']
    # Convert this JSON into an object, and load it into a Shapely object.
    # The Shapely library can then output the geometry in Well-Known-Text format
    try:
        gjson = json.loads(gjson_str)
        try:
            gjson = _add_extra_longitude_points(gjson)
        except Exception:
            # this is bad, but all we're trying to do is improve
            # certain shapes and if that fails showing the original
            # is good enough
            pass
        shape = gjson
    except ValueError:
        return None  # avoid 500 error on bad geojson in DB

    wkt_str = wkt.dumps(shape)
    return wkt_str


def cdts_asset(file_path: str, theme: Optional[bool] = True) -> str:
    return CDTS_URI + '/' + CDTS_VERSION + \
        ('/wet-boew' if theme else '/cdts') + file_path


def get_map_type() -> str:
    return str(config.get(GEO_MAP_TYPE_OPTION, GEO_MAP_TYPE_DEFAULT))


def _add_extra_longitude_points(gjson: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assume that sides of a polygon with the same latitude should
    be rendered as curves following that latitude instead of
    straight lines on the final map projection
    """
    fuzz = 0.00001
    if gjson['type'] != 'Polygon':
        return gjson
    coords = gjson['coordinates'][0]
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
    return {'coordinates': [out], 'type': 'Polygon'}


def recombinant_description_to_markup(text: str) -> Dict[str, Markup]:
    """
    Return text as HTML escaped strings joined with '<br/>, links enabled'
    """
    # very lax, this is trusted text defined in a schema not user-provided
    url_pattern = r'(https?:[^)\s"]{20,})'
    markup = []
    for i, part in enumerate(re.split(url_pattern,
                                      h.recombinant_language_text(text))):
        if i % 2:
            markup.append(Markup('<a href="{0}">{1}</a>'.format(
                part, escape(part))))
        else:
            markup.extend(Markup('<br/>'.join(
               escape(t) for t in part.split('\n')
            )))
    # extra dict because language text expected and language text helper
    # will cause plain markup to be escaped
    return {'en': Markup(''.join(markup))}


def mail_to_with_params(email_address: str, name: str,
                        subject: str, body: str) -> Markup:
    email = escape(email_address)
    author = escape(name)
    mail_subject = escape(subject)
    mail_body = escape(body)
    html = Markup('<a href="mailto:{0}?subject={2}&body={3}">{1}</a>'.format(
        email, author, mail_subject, mail_body))
    return html


def get_timeout_length() -> int:
    return int(config.get('beaker.session.timeout', 0))


def canada_check_access(package_id: str) -> bool:
    try:
        return h.check_access('package_update', {'id': package_id})
    except ObjectNotFound:
        return False


def get_user_email(user_id: str) -> str:
    '''
    Return user email address if belong to the same organization
    '''
    u = User.get(user_id)
    orgs = h.organizations_available()
    org_ids = [o['id'] for o in orgs]

    if not u or not u.is_in_groups(org_ids):
        return ""

    context = cast(Context, {'model': model,
                             'session': model.Session,
                             'keep_email': True})

    try:
        data_dict = {'id': user_id}
        user_dict = get_action('user_show')(context, data_dict)

        if 'email' in user_dict:
            return user_dict['email']
        else:
            return ""
    except ObjectNotFound:
        return ""


core_helper(plugin_loaded)


def organization_member_count(id: str) -> int:
    try:
        members = get_action('member_list')(
            cast(Context, {}),
            {
                'id': id,
                'object_type': 'user',
                'include_total': True
            })
    except ObjectNotFound:
        raise ObjectNotFound(_('Members not found'))
    except NotAuthorized:
        return -1

    return len(members)


def _build_flash_html_for_ga4(message: str, category: str,
                              caller: str, allow_html: Optional[bool] = True) -> str:
    """
    All flash messages will be given an event name and action attribute.

    data-ga-event: CALLER in format of <module>.<class>.<method> | <module>.<method>
    data-ga-action: CATEGORY in format of notice | error | success
    """
    return '<div class="canada-ga-flash" '\
           'data-ga-event="%s" data-ga-action="%s">%s</div>' % \
           (caller, category, escape(message) if
            not allow_html else Markup(message))


def _get_caller_info(stack: List['inspect.FrameInfo']) -> str:
    parentframe = stack[1][0]
    module_info = inspect.getmodule(parentframe)

    # module name
    caller_module = None
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


def flash_notice(message: str, allow_html: Optional[bool] = True):
    """
    Show a flash message of type notice

    Adding the view/action caller for GA4 Custom Events
    """
    h.flash(_build_flash_html_for_ga4(message, 'notice',
                                      _get_caller_info(inspect.stack()),
                                      allow_html=allow_html),
            category='alert-info')


def flash_error(message: str, allow_html: Optional[bool] = True):
    """
    Show a flash message of type error

    Adding the view/action caller for GA4 Custom Events
    """
    h.flash(_build_flash_html_for_ga4(message, 'error',
                                      _get_caller_info(inspect.stack()),
                                      allow_html=allow_html),
            category='alert-danger')


def flash_success(message: str, allow_html: Optional[bool] = True):
    """
    Show a flash message of type success

    Adding the view/action caller for GA4 Custom Events
    """
    h.flash(_build_flash_html_for_ga4(message, 'success',
                                      _get_caller_info(inspect.stack()),
                                      allow_html=allow_html),
            category='alert-success')


def get_loader_status_badge(resource: Dict[str, Any]) -> Union[Markup, str]:
    """
    Displays a custom badge for the status of Xloader and DataStore
    for the specified resource.
    """
    if not asbool(config.get('ckanext.canada.show_loader_badges', False)):
        return ''

    if not XLoaderFormats:
        return ''

    allowed_domains = config.get(
        'ckanext.canada.datastore_source_domain_allow_list', [])
    url = resource.get('url')
    url_parts = urlsplit(url)

    if (
      (resource.get('url_type') != 'upload' and
       url_parts.netloc not in allowed_domains) or
      not XLoaderFormats.is_it_an_xloader_format(resource.get('format'))):
        # we only want to show badges for uploads of supported xloader formats
        return ''

    is_datastore_active = resource.get('datastore_active', False)

    try:
        xloader_job = get_action("xloader_status")(
            cast(Context, {}), {"resource_id": resource.get('id')})
    except (ObjectNotFound, NotAuthorized):
        xloader_job = {}

    if xloader_job.get('status') == 'complete':
        # the xloader task is complete, show datastore active or inactive.
        # xloader will delete the datastore table at the beggining of the job run.
        # so this will only be true if the job is fully finished.
        status = 'active' if is_datastore_active else 'inactive'
    elif xloader_job.get('status') in ['pending', 'running',
                                       'running_but_viewable', 'error']:
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

    pusher_url = h.url_for('xloader.resource_data',
                           id=resource.get('package_id'),
                           resource_id=resource.get('id'))

    badge_url = h.url_for_static(
        '/static/img/badges/{lang}/datastore-{status}.svg'.format(
            lang=h.lang(), status=status))

    title = h.render_datetime(xloader_job.get('last_updated'), with_hours=True) \
        if xloader_job.get('last_updated') else ''

    # type_ignore_reason: incomplete typing
    alt_text = messages[status]  # type: ignore

    return Markup(
        '<a href="{pusher_url}" class="loader-badge">'
        '<img src="{badge_url}" alt="{alt}" title="{title}"/></a>'.format(
            pusher_url=pusher_url,
            badge_url=badge_url,
            alt=html.escape(alt_text, quote=True),
            title=html.escape(title, quote=True)))


def get_resource_view(resource_view_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns a resource view dict for the resource_view_id
    """
    try:
        return get_action('resource_view_show')(
            {}, {'id': resource_view_id})
    except ObjectNotFound:
        return None


def resource_view_type(resource_view: Dict[str, Any]) -> Optional[str]:
    view_plugin = datapreview.get_view_plugin(resource_view['view_type'])
    if not view_plugin:
        return
    return view_plugin.info().get('title')


def fgp_viewer_url(package: Dict[str, Any]) -> Optional[str]:
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


def date_field(field: str, pkg: Dict[str, Any]) -> Any:
    field_value = pkg.get(field, None)
    if field_value and ' ' in field_value:
        return field_value.split(' ')[0]
    return field_value


def split_piped_bilingual_field(field_text: Optional[str],
                                client_lang: str) -> Optional[str]:
    if field_text is not None and ' | ' in field_text:
        return field_text.split(' | ')[1 if client_lang == 'fr' else 0]
    return field_text


def search_filter_pill_link_label(search_field: str,
                                  search_extras: Dict[str, Any]) -> List[Any]:
    links_labels = []

    if search_field == 'portal_type':

        # Custom dataset type labels (suggested datasets discontinued - 2024-05-09)
        preset_choices = [{'value': 'dataset', 'label': _('Open Data')},
                          {'value': 'info', 'label': _('Open Information')},]

        # Add PD types
        for pd_type in h.recombinant_get_types():
            preset_choices.append(
                {'value': pd_type,
                 'label': _(h.recombinant_get_chromo(pd_type).get('title'))})

    elif search_field == 'status':

        preset_choices = [
            {'value': 'department_contacted',
             'label': _('Request sent to data owner - awaiting response')}]

    elif search_field == 'ready_to_publish':

        preset_choices = [{'value': 'true', 'label': _('Pending')},
                          {'value': 'false', 'label': _('Draft')},]

    else:

        preset_choices = (
            h.scheming_get_preset('canada_' + search_field) or {}).get(
                'choices', [])

        if search_field == 'collection':

            collection_choices = preset_choices
            preset_choices = [{'value': 'pd',
                               'label': _('Proactive Publication')}]

            for collection_type in collection_choices:
                preset_choices.append(collection_type)

            # Add PD types
            for pd_type in h.recombinant_get_types():
                preset_choices.append(
                    {'value': pd_type,
                     'label': _(h.recombinant_get_chromo(pd_type).get('title'))})

    def remove_filter_button_link_label(_field: str,
                                        _value: str,
                                        s_extras: Dict[str, Any],
                                        _choices: List[Any]):

        extrs = s_extras.copy() if s_extras else {}
        view_args = request.view_args
        if view_args:
            extrs.update(view_args)
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
            label = h.scheming_language_text(
                h.list_dict_filter(_choices, 'value', 'label', _value))

        return link, label

    for value in g.fields_grouped[search_field]:
        if not isinstance(value, text_type):
            for v in value:
                links_labels.append(remove_filter_button_link_label(
                    _field=search_field,
                    _value=v,
                    s_extras=search_extras,
                    _choices=preset_choices))
        else:
            links_labels.append(remove_filter_button_link_label(
                _field=search_field,
                _value=value,
                s_extras=search_extras,
                _choices=preset_choices))

    return links_labels


def ckan_to_cdts_breadcrumbs(breadcrumb_content: str) -> List[Dict[str, Any]]:
    """
    The Wet Builder requires a list of JSON objects.

    There is no good way to get the breadcrumbs from the CKAN template blocks
    into parsed JSON objects. We need to use an HTML Parser to do it.

    See: https://cdts.service.canada.ca/app/cls/WET
        /gcweb/v4_1_0/cdts/samples/breadcrumbs-en.html
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
        }, {
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


def validation_status(resource_id: str) -> str:
    try:
        validation = get_action('resource_validation_show')(
            {'ignore_auth': True},
            {'resource_id': resource_id})
        return validation.get('status')
    except (ObjectNotFound, KeyError):
        return 'unknown'


def is_user_locked(user_name: str) -> Optional[bool]:
    """
    Returns whether the user is locked out of their account or not.
    """
    try:
        throttle = get_action('security_throttle_user_show')(
            {'user': g.user}, {'user': user_name})
    except (NotAuthorized, KeyError):
        return None

    if (
      throttle and 'count' in throttle and
      throttle['count'] >= max_login_attempts()):
        return True

    return False


def available_purge_types() -> List[str]:
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


def operations_guide_link(stub: Optional[str] = None) -> str:
    """
    Return a string for a link to the Registry Operations Guide.
    """
    try:
        return json.loads(config.get('ckanext.canada.operations_guide_link'))
    except Exception:
        guide_link = {'en': 'https://open.canada.ca/en/registry-operations-guide',
                      'fr': 'https://ouvert.canada.ca/fr/guide-operations-registre'}
    guide_link = guide_link.get(h.lang(), guide_link.get('en'))
    if not stub:
        landing = 'ton-compte' if h.lang() == 'fr' else 'your-account'
        return f'{guide_link}/{landing}'
    return f'{guide_link}/{stub}'


def max_resources_per_dataset() -> Optional[int]:
    max_resource_count = config.get('ckanext.canada.max_resources_per_dataset', None)
    if max_resource_count:
        return int(max_resource_count)
