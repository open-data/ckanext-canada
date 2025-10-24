import re
import json
from logging import getLogger
from urllib.parse import urlsplit
from flask import Blueprint, has_request_context

from typing import (
    cast,
    Optional,
    Dict,
    Any,
    List,
    TYPE_CHECKING
)
from ckan.types import (
    DataDict,
    Response,
    Context
)
from flask.typing import BeforeRequestCallable

from ckan.authz import is_sysadmin
from ckan.plugins.toolkit import (
    _,
    h,
    g,
    config,
    request,
    get_action,
    asbool,
    ObjectNotFound
)

from ckanext.activity.model import activity as activity_model

from ckanext.canada.view import (
    canada_search,
    canada_prevent_pd_views,
    CanadaResourceEditView,
    CanadaResourceCreateView,
    _get_package_type_from_dict,
    CanadaDatasetEditView,
    CanadaDatasetCreateView,
)
from ckanext.canada.helpers import PUBLIC_ACTIVITY_USER, RELEASE_DATE_FACET_STEP

if TYPE_CHECKING:
    from collections import OrderedDict


log = getLogger(__name__)
fq_portal_release_date_match = re.compile(r"(portal_release_date:\"\[.*\]\")")


def can_xloader(resource_id: str) -> bool:
    """
    Only uploaded resources are allowed to be xloadered, or allowed domain sources.
    """
    # check if file is uploded
    try:
        res = get_action('resource_show')(
            {'ignore_auth': True}, {'id': resource_id})

        if (
          res.get('url_type') != 'upload' and
          res.get('url_type') != '' and
          res.get('url_type') is not None
        ):
            log.debug(
                'Only uploaded resources and allowed domain '
                'sources can be added to the Data Store.')
            return False

        if not res.get('url_type'):
            allowed_domains = config.get(
                'ckanext.canada.datastore_source_domain_allow_list', [])
            url = res.get('url')
            url_parts = urlsplit(url)
            if url_parts.netloc not in allowed_domains:
                log.debug(
                    'Only uploaded resources and allowed domain '
                    'sources can be added to the Data Store.')
                return False

    except ObjectNotFound:
        log.error('Resource %s does not exist.' % resource_id)
        return False

    # check if validation report exists
    try:
        validation = get_action('resource_validation_show')(
            {'ignore_auth': True},
            {'resource_id': res['id']})
        if validation.get('status', None) != 'success':
            log.error(
                'Only validated resources can be added to the Data Store.')
            return False

    except ObjectNotFound:
        log.error('No validation report exists for resource %s' %
                  resource_id)
        return False

    return True


def can_frictionless_validate(resource: Dict[str, Any]) -> bool:
    """
    Only uploaded resources are allowed to be validated, or allowed domain sources.
    """
    if resource.get('url_type') == 'upload':
        return True

    if not resource.get('url_type'):
        allowed_domains = config.get(
            'ckanext.canada.datastore_source_domain_allow_list', [])
        url = resource.get('url')
        url_parts = urlsplit(url)
        if url_parts.netloc in allowed_domains:
            return True

    return False


def update_citation_map(cite_data: DataDict, pkg_dict: DataDict):
    """
    Updates cite_data for the Canada dataset schema.
    """
    cite_data['container_title'] = _(cite_data['container_title'])
    lang = 'en'
    try:
        lang = h.lang()
    except RuntimeError:
        pass

    if org := pkg_dict.get('org_section', {}).get(lang):
        cite_data['publisher'] += ' - ' + org

    cite_data['author'] = []
    if pkg_dict.get('creator'):
        cite_data['author'].append({
            'family': pkg_dict['creator']
        })
    if contributor := pkg_dict.get('contributor', {}).get(lang):
        cite_data['author'].append({
            'family': contributor
        })
    if pkg_dict.get('credit'):
        for e in pkg_dict['credit']:
            if creditor := e.get('credit_name', {}).get(lang):
                cite_data['author'].append({
                    'family': creditor
                })
    if not cite_data['author']:
        cite_data.pop('author', None)


# type_ignore_reason: incomplete typing
def _redirect_pd_dataset_endpoints() -> Optional[Response]:
    """
    Runs before request for /dataset and /dataset/<pkg_id>/resource

    Checks if the actual package type is a PD Type and redirects it
    to the correct Recombinant route.
    """
    if has_request_context() and hasattr(request, 'view_args'):
        if not request.view_args:
            return
        id = request.view_args.get('id')
        if not id:
            return
        package_type = request.view_args.get('package_type')
        package_type = _get_package_type_from_dict(id, package_type)
        if package_type in h.recombinant_get_types():
            return h.redirect_to('canada.type_redirect',
                                 resource_name=package_type)


def modify_core_dataset_blueprint(package_type: str, blueprint: Blueprint):
    blueprint.add_url_rule(
        '/edit/<id>',
        endpoint='canada_edit_%s' % package_type,
        view_func=CanadaDatasetEditView.as_view(str('edit')),
        methods=['GET', 'POST']
    )
    blueprint.add_url_rule(
        '/new',
        endpoint='canada_new_%s' % package_type,
        view_func=CanadaDatasetCreateView.as_view(str('new')),
        methods=['GET', 'POST']
    )
    blueprint.add_url_rule(
        '/',
        endpoint='canada_search_%s' % package_type,
        view_func=canada_search,
        methods=['GET'],
        strict_slashes=False
    )
    # redirect PD endpoints accessed from /dataset/<pd pkg id>
    blueprint.before_request(cast(BeforeRequestCallable,
                                  _redirect_pd_dataset_endpoints))


def modify_core_resource_blueprint(package_type: str, blueprint: Blueprint):
    """
    Extends the Core Resource Edit/Create views.

    Redirects PD Type resources to their correct Recombinant routes.
    """
    blueprint.add_url_rule(
        '/<resource_id>/edit',
        endpoint='canada_resource_edit_%s' % package_type,
        view_func=CanadaResourceEditView.as_view(str('edit')),
        methods=['GET', 'POST']
    )
    blueprint.add_url_rule(
        '/new',
        endpoint='canada_resource_new_%s' % package_type,
        view_func=CanadaResourceCreateView.as_view(str('new')),
        methods=['GET', 'POST']
    )
    # redirect PD endpoints accessed from /dataset/<pd pkg id>/resource
    blueprint.before_request(cast(BeforeRequestCallable,
                                  _redirect_pd_dataset_endpoints))


def raise_exception_show_non_published_dataset(pkg_dict: Dict[str, Any]):
    """
    Raise NotFound for datasets on the portal which have:
        - imso_approval=False
        - ready_to_publish=False
        - portal_release_date=None
        - private=True
        - state!=active
    """
    if has_request_context() and not h.is_registry_domain():
        if (
            pkg_dict.get('type') not in ['info', 'dataset', 'prop'] or
            not asbool(pkg_dict.get('imso_approval')) or
            not asbool(pkg_dict.get('ready_to_publish')) or
            not pkg_dict.get('portal_release_date') or
            asbool(pkg_dict.get('private')) or
            pkg_dict.get('state') != 'active'
        ):
            raise ObjectNotFound()


def expand_solr_french_extras(search_results: Dict[str, Any]):
    """
    Pops some Extra key/values into the result dict for dataset SOLR objects.
    """
    for result in search_results.get('results', []):
        for extra in result.get('extras', []):
            if extra.get('key') in ['title_fra', 'notes_fra']:
                result[extra['key']] = extra['value']


def prevent_core_views_for_pd_types() -> List[Blueprint]:
    """
    Prevents all Core Dataset and Resources Views for all the PD types.
    Will type_redirect them to the pd_type. Will allow /<pd_type>/activity
    """
    blueprints = []
    for pd_type in h.recombinant_get_types():
        blueprint = Blueprint(
            'canada_%s' % pd_type,
            __name__,
            url_prefix='/%s' % pd_type,
            url_defaults={'package_type': pd_type})
        blueprint.add_url_rule(
            '/',
            endpoint='canada_search_%s' % pd_type,
            view_func=canada_search,
            methods=['GET']
        )
        blueprint.add_url_rule(
            '/<path:uri>',
            endpoint='canada_prevent_%s' % pd_type,
            view_func=canada_prevent_pd_views,
            methods=['GET', 'POST']
        )
        blueprints.append(blueprint)
    return blueprints


def activity_dictize(activity: activity_model.Activity,
                     context: Context) -> dict[str, Any]:
    """
    Monkey-patch for a vanity username for activity on the Portal.

    This prevents user information from showing in activity objects.
    """
    activity_dict = activity_model.table_dictize(activity, context)
    try:
        if not g.user:
            activity_dict['user_id'] = PUBLIC_ACTIVITY_USER
    except RuntimeError:
        pass
    return activity_dict


def update_facets(facets_dict: 'OrderedDict[str, Any]'):
    facets_dict.update({
        'portal_type': _('Portal Type'),
        'organization': _('Organization'),
        'collection': _('Collection Type'),
        'keywords': _('Keywords'),
        'keywords_fra': _('Keywords'),
        'subject': _('Subject'),
        'res_format': _('Format'),
        'res_type': _('Resource Type'),
        'frequency': _('Maintenance and Update Frequency'),
        'capacity': _('Published'),
        'ready_to_publish': _('Record Status'),
        'imso_approval': _('IMSO Approval'),
        'jurisdiction': _('Jurisdiction'),
        'status': _('Suggestion Status'),
    })


def update_dataset_search_params(search_params: Dict[str, Any]):
    # We're going to group portal_release_date into two bins
    # to today and after today.
    search_params['facet.range'] = 'portal_release_date'
    search_params['facet.range.start'] = 'NOW/DAY-%sYEARS' % \
        RELEASE_DATE_FACET_STEP
    search_params['facet.range.end'] = 'NOW/DAY+%sYEARS' % \
        RELEASE_DATE_FACET_STEP
    search_params['facet.range.gap'] = '+%sYEARS' % \
        RELEASE_DATE_FACET_STEP

    if 'fq_list' not in search_params:
        search_params['fq_list'] = []

    # FIXME: so terrible. hack out WET4 wbdisable parameter
    try:
        search_params['fq'] = search_params['fq'].replace(
            'wbdisable:"true"', '').replace(
            'wbdisable:"false"', '')
    except Exception:
        pass

    try:
        g.fields_grouped.pop('wbdisable', None)
    except Exception:
        pass

    # search extras for ckan-admin/publish route.
    # we only want to show ready to publish,
    # approved datasets without a release date.
    if has_request_context() and 'ckan-admin/publish' in request.url:
        search_params['extras']['ready_to_publish'] = 'true'
        search_params['extras']['imso_approval'] = 'true'
        search_params['fq_list'] += [
            '+ready_to_publish:"true"',
            '+imso_approval:"true"',
            '-portal_release_date:*']

    # CKAN Core search view wraps all fq values with double quotes.
    # We need to remove double quotes from the portal_release_date queries.
    if 'fq' in search_params:
        for release_date_query in re.findall(fq_portal_release_date_match,
                                             search_params['fq']):
            search_params['fq'] = search_params['fq'].replace(
                release_date_query, release_date_query.replace('"', ''))

    # NOTE: is_registry_domain returns True outside of flask context
    if not h.is_registry_domain():
        # NOTE: wilcards must come last...
        search_params['fq_list'] += [
            '+imso_approval:"true"',
            '+state:"active"',
            '+capacity:"public"',
            '+dataset_type:(info OR dataset)',
            '+portal_release_date:*']
    else:
        try:
            contextual_user = search_params.get('extras', {}).pop(
                '__CONTEXTUAL_USER__', None)
        except (TypeError, RuntimeError, AttributeError):
            contextual_user = None
        if not contextual_user:
            search_params['fq_list'] += ['-organization:*']
        elif not is_sysadmin(contextual_user):
            org_names = [o['name'] for o in get_action(
                'organization_list_for_user')({'user': contextual_user},
                                              {'permission': 'read'})]
            search_params['fq_list'] += [
                '+organization:(%s)' % ' OR '.join(org_names)]


def update_dataset_for_solr(data_dict: Dict[str, Any]):
    """
    Parse CKAN schema into the configured SOLR schema.

    See: ckanext-canada/conf/solr/schema.xml for SOLR schema
    """
    kw = json.loads(data_dict.get('extras_keywords', '{}'))
    data_dict['keywords'] = kw.get('en', [])
    data_dict['keywords_fra'] = kw.get('fr', kw.get('fr-t-en', []))
    data_dict['catalog_type'] = data_dict.get('type', '')

    data_dict['subject'] = json.loads(data_dict.get('subject', '[]'))
    data_dict['topic_category'] = json.loads(data_dict.get(
        'topic_category', '[]'))
    data_dict['spatial_representation_type'] = []
    if (
      data_dict.get('spatial_representation_type') and
      isinstance(data_dict.get('spatial_representation_type'), str)
    ):
        rep_type: str = data_dict.get('spatial_representation_type', '')
        try:
            data_dict['spatial_representation_type'] = json.loads(rep_type)
        except (TypeError, ValueError):
            data_dict['spatial_representation_type'] = []

    if data_dict.get('portal_release_date'):
        data_dict.pop('ready_to_publish', None)
    elif data_dict.get('ready_to_publish') == 'true':
        data_dict['ready_to_publish'] = 'true'
    else:
        data_dict['ready_to_publish'] = 'false'

    try:
        geno = h.recombinant_get_geno(data_dict['type']) or {}
    except AttributeError:
        pass
    else:
        data_dict['portal_type'] = geno.get('portal_type', data_dict['type'])
        if 'collection' in geno:
            data_dict['collection'] = geno['collection']

    # need to keep fgp_viewer in the index for Advanced Search App
    if 'fgp_viewer' in data_dict.get('display_flags', []):
        data_dict['fgp_viewer'] = 'map_view'

    titles = json.loads(data_dict.get('title_translated', '{}'))
    data_dict['title_fr'] = titles.get('fr', '')
    data_dict['title_string'] = titles.get('en', '')

    if data_dict['type'] == 'prop':
        status = data_dict.get('status')
        data_dict['status'] = status[-1]['reason'] if \
            status else 'department_contacted'

    if data_dict.get('credit'):
        for i, cr in enumerate(data_dict['credit']):
            cr.pop('__extras', None)
            # credit is a string multiValue in SOLR,
            # need to json stringify for SOLR 9+
            data_dict['credit'][i] = json.dumps(cr)

    if data_dict.get('relationship'):
        data_dict['related_relationship'] = [rel['related_relationship'] for
                                             rel in data_dict['relationship']]
        data_dict['related_type'] = [rel['related_type'] for
                                     rel in data_dict['relationship']]
    data_dict.pop('relationship', None)

    if data_dict['type'] in ['dataset', 'info']:
        if data_dict.get('private', True):
            data_dict['capacity'] = 'private'
        else:
            data_dict['capacity'] = 'public'
    else:
        data_dict['capacity'] = 'private'


def update_datastore_dict_for_legacy(field: Dict[str, Any],
                                     plugin_data: Dict[str, Any]):
    """
    This is a workaround for legacy DataDictionaries.
    """
    if 'info' or '_info' in plugin_data and 'info' not in field:
        if 'info' in plugin_data:
            field['info'] = plugin_data.get('info', {})
        elif '_info' in plugin_data:
            field['info'] = plugin_data.get('_info', {})
