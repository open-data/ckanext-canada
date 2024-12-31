import re
import json
from flask import has_request_context, Blueprint
from urllib.parse import urlsplit
import logging

from typing import Optional, List, Dict, cast
from flask.typing import BeforeRequestCallable
from ckan.types import Context, Response, Any

import ckan.plugins as p
from ckan.plugins.toolkit import g, h, request

from ckanext.datastore.interfaces import IDataDictionaryForm
from ckanext.scheming.plugins import SchemingDatasetsPlugin
from ckanext.canada.helpers import RELEASE_DATE_FACET_STEP
from ckanext.canada.view import (
    CanadaDatasetEditView,
    CanadaDatasetCreateView,
    CanadaResourceEditView,
    CanadaResourceCreateView,
    canada_search,
    canada_prevent_pd_views,
    _get_package_type_from_dict
)


log = logging.getLogger(__name__)
fq_portal_release_date_match = re.compile(r"(portal_release_date:\"\[.*\]\")")


class CanadaDatasetsPlugin(SchemingDatasetsPlugin):
    """
    Plugin for dataset and resource
    """
    p.implements(p.IDatasetForm, inherit=True)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.IBlueprint)
    p.implements(IDataDictionaryForm, inherit=True)

    try:
        from ckanext.validation.interfaces import IDataValidation
    except ImportError:
        log.warning('failed to import ckanext-validation interface')
    else:
        p.implements(IDataValidation, inherit=True)

    # IBlueprint
    def get_blueprint(self) -> List[Blueprint]:
        """
        Prevents all Core Dataset and Resources Views
        for all the PD types. Will type_redirect them
        to the pd_type. Will allow /<pd_type>/activity
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

    # type_ignore_reason: incomplete typing
    def _redirect_pd_dataset_endpoints(blueprint: Blueprint  # type: ignore
                                       ) -> Optional[Response]:
        """
        Runs before request for /dataset and /dataset/<pkg id>/resource

        Checks if the actual package type is a PD type and redirects it.
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

    # IDatasetForm
    def prepare_dataset_blueprint(self, package_type: str,
                                  blueprint: Blueprint) -> Blueprint:
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
                                      self._redirect_pd_dataset_endpoints))
        return blueprint

    # IDatasetForm
    def prepare_resource_blueprint(self, package_type: str,
                                   blueprint: Blueprint) -> Blueprint:
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
                                      self._redirect_pd_dataset_endpoints))
        return blueprint

    # IDataValidation
    def can_validate(self, context: Context, resource: Dict[str, Any]):
        """
        Only uploaded resources are allowed to be
        validated, or allowed domain sources.
        """
        if resource.get('url_type') == 'upload':
            return True

        if not resource.get('url_type'):
            allowed_domains = p.toolkit.config.get(
                'ckanext.canada.datastore_source_domain_allow_list', [])
            url = resource.get('url')
            url_parts = urlsplit(url)
            if url_parts.netloc in allowed_domains:
                return True

        return False

    # IPackageController
    def before_dataset_search(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        # We're going to group portal_release_date into two bins - to today and
        # after today.
        search_params['facet.range'] = 'portal_release_date'
        search_params['facet.range.start'] = 'NOW/DAY-%sYEARS' % \
            RELEASE_DATE_FACET_STEP
        search_params['facet.range.end'] = 'NOW/DAY+%sYEARS' % \
            RELEASE_DATE_FACET_STEP
        search_params['facet.range.gap'] = '+%sYEARS' % \
            RELEASE_DATE_FACET_STEP

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
            search_params['fq'] += '+ready_to_publish:"true", '\
                '+imso_approval:"true", -portal_release_date:*'

        # CKAN Core search view wraps all fq values with double quotes.
        # We need to remove double quotes from the portal_release_date queries.
        if 'fq' in search_params:
            for release_date_query in re.findall(fq_portal_release_date_match,
                                                 search_params['fq']):
                search_params['fq'] = search_params['fq'].replace(
                    release_date_query, release_date_query.replace('"', ''))

        return search_params

    # IPackageController
    def after_dataset_search(self, search_results: Dict[str, Any],
                             search_params: Dict[str, Any]) -> Dict[str, Any]:
        for result in search_results.get('results', []):
            for extra in result.get('extras', []):
                if extra.get('key') in ['title_fra', 'notes_fra']:
                    result[extra['key']] = extra['value']

        return search_results

    # IPackageController
    def before_dataset_index(self, data_dict: Dict[str, Any]) -> Dict[str, Any]:
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
          isinstance(data_dict.get('spatial_representation_type'), str)):
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

        return data_dict

    # IDataDictionaryForm
    def update_datastore_info_field(self, field: Dict[str, Any],
                                    plugin_data: Dict[str, Any]) -> Dict[str, Any]:
        if 'info' or '_info' in plugin_data and 'info' not in field:
            if 'info' in plugin_data:
                field['info'] = plugin_data.get('info', {})
            elif '_info' in plugin_data:
                field['info'] = plugin_data.get('_info', {})
        return field
