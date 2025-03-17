from typing import Any, Union, Optional, List, TYPE_CHECKING, Type, Dict, Tuple
from ckan.types import (
    Action,
    ChainedAction,
    AuthFunction,
    ChainedAuthFunction,
    CKANApp
)
from ckan.common import CKANConfig

import os
from flask import Blueprint
from click import Command

import ckan.plugins as p
from ckan.lib.plugins import DefaultTranslation
from ckan.plugins.toolkit import _, g, h
import ckan.lib.helpers as core_helpers
import ckan.lib.formatters as formatters

from ckanext.activity.logic.validators import object_id_validators
from ckanext.tabledesigner.interfaces import IColumnTypes
from ckanext.tabledesigner.column_types import ColumnType
from ckanext.canada import column_types as coltypes
from ckanext.canada.pd import get_commands as get_pd_commands
from ckanext.canada.view import canada_views
from ckanext.canada import cli
from ckanext.canada import logic
from ckanext.canada import auth

if TYPE_CHECKING:
    from collections import OrderedDict


class CanadaPublicPlugin(p.SingletonPlugin, DefaultTranslation):
    """
    Plugin for public-facing version of Open Government site, aka the "portal"
    This plugin requires the DataGCCAForms plugin
    """
    p.implements(p.IConfigurer)
    p.implements(p.IAuthFunctions)
    p.implements(p.IFacets)
    p.implements(p.ITranslation)
    p.implements(p.IMiddleware, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IClick)
    p.implements(IColumnTypes)
    p.implements(p.IBlueprint)

    # DefaultTranslation, ITranslation
    @classmethod
    def i18n_domain(cls) -> str:
        return 'ckanext-canada'

    @classmethod
    def i18n_directory(cls) -> str:
        return os.path.join(os.path.dirname(str(__file__)), '../i18n')

    @classmethod
    def i18n_locales(cls) -> List[str]:
        return ['en', 'fr']

    # IConfigurer
    def update_config(self, config: 'CKANConfig'):
        config['ckan.auth.public_user_details'] = False
        config['ckan.auth.public_activity_stream_detail'] = False

        recombinant_definitions = config.get('recombinant.definitions', '')
        assert 'ckanext.canada:tables/ati.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/briefingt.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/qpnotes.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/contracts.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/contractsa.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/grants.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/grantsmonthly.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/hospitalityq.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/reclassification.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/travela.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/travelq.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/wrongdoing.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/inventory.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/consultations.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/service.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/dac.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/nap5.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/experiment.yaml' in recombinant_definitions
        assert 'ckanext.canada:tables/adminaircraft.yaml' in recombinant_definitions

        config['ckan.search.show_all_types'] = True
        config['ckan.gravatar_default'] = 'disabled'
        config['search.facets.limit'] = 200  # because org list

        scheming_presets = config.get('scheming.presets', '')
        if 'validation' not in scheming_presets:
            assert 'ckanext.scheming:presets.json' in scheming_presets
            assert 'ckanext.fluent:presets.json' in scheming_presets
            assert 'ckanext.canada:schemas/presets.yaml' in scheming_presets
            assert 'ckanext.canada:schemas/validation_placeholder_presets.yaml' in \
                scheming_presets

        scheming_dataset_schemas = config.get('scheming.dataset_schemas', '')
        assert 'ckanext.canada:schemas/dataset.yaml' in scheming_dataset_schemas
        assert 'ckanext.canada:schemas/info.yaml' in scheming_dataset_schemas
        assert 'ckanext.canada:schemas/prop.yaml' in scheming_dataset_schemas

        scheming_organization_schemas = config.get('scheming.organization_schemas', '')
        assert 'ckanext.canada:schemas/organization.yaml' in \
            scheming_organization_schemas

        # Pretty output for Feeds
        config['ckan.feeds.pretty'] = True

        # Enable our custom DCAT profile.
        config['ckanext.dcat.rdf.profiles'] = 'euro_dcat_ap_2'

        # Enable license restriction
        config['ckan.dataset.restrict_license_choices'] = True

        # monkey patch helpers.py pagination method
        core_helpers.Page.pager = _wet_pager
        core_helpers.SI_number_span = _SI_number_span_close

        core_helpers.build_nav_main = build_nav_main

        # migration from `canada_activity` and `ckanext-extendedactivity` - Aug 2022
        # migrated from `ckan` canada fork for resource view activities - Jan 2024
        # migrated from `activity` for ckan 2.10 upgrade - June 2024
        object_id_validators.update({
            'new resource view': 'package_id_exists',
            'changed resource view': 'package_id_exists',
            'deleted resource view': 'package_id_exists',
        })

    # IFacets
    def dataset_facets(self, facets_dict: 'OrderedDict[str, Any]',
                       package_type: str) -> 'OrderedDict[str, Any]':
        ''' Update the facets_dict and return it. '''

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
            'ready_to_publish': _('Record Status'),
            'imso_approval': _('IMSO Approval'),
            'jurisdiction': _('Jurisdiction'),
            'status': _('Suggestion Status'),
            })

        return facets_dict

    # IFacets
    # FIXME: remove `group_facets` method once issue
    # https://github.com/ckan/ckan/issues/7017 is patched into <2.9
    def group_facets(self, facets_dict: 'OrderedDict[str, Any]',
                     group_type: str, package_type: str) -> 'OrderedDict[str, Any]':
        ''' Update the facets_dict and return it. '''
        if group_type == 'organization':
            return self.dataset_facets(facets_dict, package_type)
        return facets_dict

    # IFacets
    def organization_facets(self, facets_dict: 'OrderedDict[str, Any]',
                            organization_type: str, package_type: str
                            ) -> 'OrderedDict[str, Any]':
        return self.dataset_facets(facets_dict, package_type)

    # IActions
    def get_actions(self) -> Dict[str, Union[Action, ChainedAction]]:
        return {
            'resource_view_show': logic.canada_resource_view_show,
            'resource_view_list': logic.canada_resource_view_list,
            'job_list': logic.canada_job_list,
            'registry_jobs_running': logic.registry_jobs_running,
            'datastore_search': logic.canada_datastore_search,
        }

    # IAuthFunctions
    def get_auth_functions(self) -> Dict[str, Union[AuthFunction,
                                                    ChainedAuthFunction]]:
        return {
            'datastore_create': auth.datastore_create,
            'datastore_delete': auth.datastore_delete,
            'datastore_upsert': auth.datastore_upsert,
            'view_org_members': auth.view_org_members,
            'registry_jobs_running': auth.registry_jobs_running,
            'recently_changed_packages_activity_list':
                auth.recently_changed_packages_activity_list,
        }

    # IMiddleware
    def make_middleware(self, app: CKANApp, config: 'CKANConfig') -> CKANApp:
        return LogExtraMiddleware(app, config)

    # IClick
    def get_commands(self) -> List[Command]:
        return [cli.get_commands(), get_pd_commands()]

    # IColumnTypes
    def column_types(self, existing_types: Dict[str, Type[ColumnType]]):
        return dict(
            existing_types,
            province=coltypes.Province,
            crabusnum=coltypes.CRABusinessNumber,
        )

    # IBlueprint
    def get_blueprint(self) -> List[Blueprint]:
        return [canada_views]


class LogExtraMiddleware(object):
    def __init__(self, app: Any, config: 'CKANConfig'):
        self.app = app

    def __call__(self, environ: Any, start_response: Any) -> Any:
        def _start_response(status: str,
                            response_headers: List[Tuple[str, str]],
                            exc_info: Optional[Any] = None):
            extra = []
            try:
                contextual_user = g.user
            except (TypeError, RuntimeError, AttributeError):
                contextual_user = None
            if contextual_user:
                log_extra = g.log_extra if hasattr(g, 'log_extra') else ''
                # FIXME: make sure username special chars are handled
                # the values in the tuple HAVE to be str types.
                extra = [('X-LogExtra', f'user={contextual_user} {log_extra}')]

            return start_response(
                status,
                response_headers + extra,
                exc_info)

        return self.app(environ, _start_response)


def _wet_pager(self: core_helpers.Page, *args: Any, **kwargs: Any):
    # a custom pagination method, because CKAN doesn't
    # expose the pagination to the templates,
    # and instead hardcodes the pagination html in helpers.py
    kwargs.update(
        format="<ul class='pagination'>$link_previous ~2~ $link_next</ul>",
        symbol_previous=core_helpers._('Previous'),
        symbol_next=core_helpers._('Next'),
        curpage_attr={'class': 'active'}
    )

    return super(core_helpers.Page, self).pager(*args, **kwargs)


def _SI_number_span_close(number: Union[str, int]):
    ''' outputs a span with the number in SI unit eg 14700 -> 14.7k '''
    number = int(number)
    if number < 1000:
        output = h.literal('<span>')
    else:
        output = h.literal(
            '<span title="' + formatters.localised_number(number) + '">')
    return output + formatters.localised_SI_number(number) + h.literal('</span>')


# Monkey Patched to inlude the 'list-group-item' class
# TODO: Clean up and convert to proper HTML templates
def build_nav_main(*args: Any):
    ''' build a set of menu items.

    args: tuples of (menu type, title) eg ('login', _('Login'))
    outputs <li><a href="...">title</a></li>
    '''
    output = ''
    for item in args:
        menu_item, title = item[:2]
        if len(item) == 3 and not core_helpers.check_access(item[2]):
            continue
        output += core_helpers._make_menu_item(
            menu_item, title, class_='list-group-item')
    return output
