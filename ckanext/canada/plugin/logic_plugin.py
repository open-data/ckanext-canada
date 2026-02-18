from flask import Blueprint, has_request_context
from click import Command

from ckan.types import (
    Action,
    ChainedAction,
    AuthFunction,
    ChainedAuthFunction,
    Context,
    DataDict,
    CKANApp,
    Validator,
    Schema
)
from typing import (
    Dict,
    Union,
    Any,
    Tuple,
    Optional,
    List,
    Type,
    TYPE_CHECKING
)
from ckan.common import CKANConfig
from ckanext.tabledesigner.column_types import ColumnType

import ckan.plugins as p
from ckan import model

from ckan.plugins.toolkit import (
    h,
    g,
    get_validator,
)

from ckanext.scheming.plugins import SchemingDatasetsPlugin
from ckanext.security.plugin import CkanSecurityPlugin

from ckanext.datastore.interfaces import IDataDictionaryForm
from ckanext.tabledesigner.interfaces import IColumnTypes
from ckanext.citeproc.interfaces import ICiteProcMappings
from ckanext.validation.interfaces import IDataValidation
from ckanext.xloader.interfaces import IXloader

from ckanext.canada.pd import get_commands as get_pd_commands
from ckanext.canada.cli import get_commands as get_canada_commands
from ckanext.canada.logic import get_action_methods
from ckanext.canada.auth import get_auth_methods
from ckanext.canada.validators import get_validator_methods
from ckanext.canada.column_types import get_datastore_column_types
from ckanext.canada import dataset
from ckanext.canada import config as canada_config
from ckanext.canada.middleware import LogExtraMiddleware

if TYPE_CHECKING:
    from collections import OrderedDict


class CanadaLogicPlugin(SchemingDatasetsPlugin, CkanSecurityPlugin):
    """
    Plugin for all of the logic of the Open Government Canada Portal & Registry.

    See theme_plugin.py::CanadaThemePlugin for templates and helpers.
    """
    p.implements(IXloader, inherit=True)
    p.implements(p.IFacets)
    p.implements(p.IPackageController, inherit=True)
    p.implements(IDataDictionaryForm, inherit=True)
    p.implements(IDataValidation, inherit=True)
    p.implements(p.IMiddleware, inherit=True)
    p.implements(p.IApiToken, inherit=True)
    p.implements(IColumnTypes)
    p.implements(ICiteProcMappings)
    # NOTE: SchemingDatasetsPlugin implements:
    #           p.IConfigurer
    #           p.IConfigurable
    #           p.IDatasetForm
    #           p.IActions
    #           p.IValidators
    # NOTE: CkanSecurityPlugin implements:
    #           p.IConfigurer
    #           p.IResourceController
    #           p.IActions
    #           p.IAuthFunctions
    #           p.IValidators
    #           p.IAuthenticator
    #           p.IBlueprint
    #           p.IClick

    def update_config(self, config: 'CKANConfig'):
        """
        Add template directories and set initial configuration values.

        Implement of: ckan.plugins.interfaces.IConfigurer
        SubMethod of: SchemingDatasetsPlugin, CkanSecurityPlugin
        """
        SchemingDatasetsPlugin.update_config(self, config)
        CkanSecurityPlugin.update_config(self, config)
        canada_config.update_config(config)

    def configure(self, config: 'CKANConfig'):
        """
        Set initial configuration values after the app stack has been setup
        but prior to requests, this happens after IConfigurer::update_config

        Implement of: ckan.plugins.interfaces.IConfigurable
        SubMethod of: SchemingDatasetsPlugin
        """
        super().configure(config)
        canada_config.configure()

    def get_commands(self) -> List[Command]:
        """
        Adds sub commands to the ckan command line.

        Implement of: ckan.plugins.interfaces.IClick
        SuMethod of: CkanSecurityPlugin
        """
        # type_ignore_reason: incomplete typing
        return super().get_commands() + [
            get_canada_commands(), get_pd_commands()]  # type: ignore

    def dataset_facets(self, facets_dict: 'OrderedDict[str, Any]',
                       package_type: str) -> 'OrderedDict[str, Any]':
        """
        Updates the Search Facets for Datasets.

        Implement of: ckan.plugins.interfaces.IFacets
        """
        dataset.update_facets(facets_dict)
        return facets_dict

    def group_facets(self, facets_dict: 'OrderedDict[str, Any]',
                     group_type: str, package_type: str) -> 'OrderedDict[str, Any]':
        """
        Updates the Search Facets for Groups & Organizations.

        Implement of: ckan.plugins.interfaces.IFacets
        """
        # FIXME: remove `group_facets` method once issue
        # https://github.com/ckan/ckan/issues/7017 is patched into <2.9
        if group_type == 'organization':
            return self.dataset_facets(facets_dict, package_type)
        return facets_dict

    def organization_facets(self, facets_dict: 'OrderedDict[str, Any]',
                            organization_type: str, package_type: str
                            ) -> 'OrderedDict[str, Any]':
        """
        Updates the Search Facets for Organizations.

        Implement of: ckan.plugins.interfaces.IFacets
        """
        return self.dataset_facets(facets_dict, package_type)

    def get_blueprint(self) -> List[Blueprint]:
        """
        Add Flask blueprint/view routes to the Flask app.

        Implement of: ckan.plugins.interfaces.IBlueprint
        SubMethod of: CkanSecurityPlugin
        """
        return super().get_blueprint() + dataset.prevent_core_views_for_pd_types()

    def before_create(self, context: Context, resource: Dict[str, Any]):
        """
        Override before_create from CkanSecurityPlugin.
        Want to use the methods in scheming instead of before_create.

        Implement of: ckan.plugins.interfaces.IResourceController
        SubMethod of: CkanSecurityPlugin
        """

    def before_update(self, context: Context,
                      current: Dict[str, Any], resource: Dict[str, Any]):
        """
        Override before_update from CkanSecurityPlugin.
        Want to use the methods in scheming instead of before_update.

        Implement of: ckan.plugins.interfaces.IResourceController
        SubMethod of: CkanSecurityPlugin
        """

    def before_resource_create(self, context: Context, resource: Dict[str, Any]):
        """
        Override before_resource_create from CkanSecurityPlugin.
        Want to use the methods in scheming instead of before_resource_create.

        Implement of: ckan.plugins.interfaces.IResourceController
        SubMethod of: CkanSecurityPlugin
        """

    def before_resource_update(self, context: Context,
                               current: Dict[str, Any], resource: Dict[str, Any]):
        """
        Override before_resource_update from CkanSecurityPlugin.
        Want to use the methods in scheming instead of before_resource_update.

        Implement of: ckan.plugins.interfaces.IResourceController
        SubMethod of: CkanSecurityPlugin
        """

    def create(self, pkg: 'model.Package'):
        """
        Force Private on package types that should never be visible on the Portal

        Implement of: ckan.plugins.interfaces.IPackageController
        """
        non_portal_types = h.recombinant_get_types() + ['prop', 'doc']
        if pkg.type in non_portal_types:
            pkg.private = True

    def edit(self, pkg: 'model.Package'):
        """
        Force Private on package types that should never be visible on the Portal

        Implement of: ckan.plugins.interfaces.IPackageController
        """
        non_portal_types = h.recombinant_get_types() + ['prop', 'doc']
        if pkg.type in non_portal_types:
            pkg.private = True

    def after_dataset_show(self, context: Context, pkg_dict: Dict[str, Any]):
        """
        Manipulates the Dataset dict after the package_show action method.

        Implement of: ckan.plugins.interfaces.IPackageController
        """
        dataset.raise_exception_show_non_published_dataset(pkg_dict)
        return

    def after_dataset_search(self, search_results: Dict[str, Any],
                             search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manipulates the SOLR search results after the SOLR query has executed.

        Implement of: ckan.plugins.interfaces.IPackageController
        """
        dataset.expand_solr_french_extras(search_results)
        return search_results

    def before_dataset_search(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manipulates the SOLR query dict before the SOLR query has been parsed executed.

        Implement of: ckan.plugins.interfaces.IPackageController
        """
        dataset.update_dataset_search_params(search_params)
        return search_params

    def before_dataset_index(self, data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manipulates the Dataset dict before it is inserted as a SOLR record.

        Implement of: ckan.plugins.interfaces.IPackageController
        """
        dataset.update_dataset_for_solr(data_dict)
        return data_dict

    def update_datastore_info_field(self, field: Dict[str, Any],
                                    plugin_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manipulates the DataStore dict. This is a workaround
        for legacy DataDictionaries.

        Implement of: ckanext.datastore.interfaces.IDataDictionaryForm
        """
        dataset.update_datastore_dict_for_legacy(field, plugin_data)
        return field

    def can_validate(self, context: Context, resource: Dict[str, Any]):
        """
        Only uploaded resources are allowed to be validated, or allowed domain sources.

        Implement of: ckanext.validation.interfaces.IDataValidation
        """
        return dataset.can_frictionless_validate(resource)

    def prepare_dataset_blueprint(self, package_type: str,
                                  blueprint: Blueprint) -> Blueprint:
        """
        Modify the Core Dataset blueprint.

        Implement of: ckan.plugins.interfaces.IDatasetForm
        SubMethod of: SchemingDatasetsPlugin
        """
        super().prepare_dataset_blueprint(package_type, blueprint)
        dataset.modify_core_dataset_blueprint(package_type, blueprint)
        return blueprint

    def prepare_resource_blueprint(self, package_type: str,
                                   blueprint: Blueprint) -> Blueprint:
        """
        Modify the Core Resource blueprint.

        Implement of: ckan.plugins.interfaces.IDatasetForm
        SubMethod of: SchemingDatasetsPlugin
        """
        super().prepare_dataset_blueprint(package_type, blueprint)
        dataset.modify_core_resource_blueprint(package_type, blueprint)
        return blueprint

    def get_validators(self) -> Dict[str, Validator]:
        """
        Override, extend, and add navl validations methods.

        Implement of: ckan.plugins.interfaces.IValidators
        """
        security_validators_dict = CkanSecurityPlugin.get_validators(self) or {}
        custom_validators_dict = get_validator_methods()
        return security_validators_dict | custom_validators_dict

    def make_middleware(self, app: CKANApp, config: 'CKANConfig') -> CKANApp:
        """
        Adds a Flask middleware object to the Flask app stack.

        Implement of: ckan.plugins.interfaces.IMiddleware
        """
        LogExtraMiddleware(app, config)
        return app

    def abort(self, status_code: int, detail: str,
              headers: Optional[Dict[str, Any]],
              comment: Optional[str]) -> Tuple[
                  int, str, Optional[Dict[str, Any]], Optional[str]]:
        """
        All 403 status should be made into 404s for non-logged in users.

        Implement of: ckan.plugins.interfaces.IAuthenticator
        """
        if has_request_context() and g.user:
            return (status_code, detail, headers, comment)
        if status_code == 403:
            return (404, detail, headers, comment)
        return (status_code, detail, headers, comment)

    def create_api_token_schema(self, schema: Schema) -> Schema:
        """
        Modify the API Token Schema.

        Implement of: ckan.plugins.interfaces.IApiToken
        """
        api_token_name_validator = get_validator(
            'canada_api_token_name_validator')
        # type_ignore_reason: incomplete typing
        schema['name'].append(api_token_name_validator)  # type: ignore
        return schema

    def get_actions(self) -> Dict[str, Union[Action, ChainedAction]]:
        """
        Override, extend, and add logic action methods.

        Implement of: ckan.plugins.interfaces.IActions
        SubMethod of: SchemingDatasetsPlugin, CkanSecurityPlugin
        """
        return SchemingDatasetsPlugin.get_actions(self) \
            | CkanSecurityPlugin.get_actions(self) \
            | get_action_methods()

    def get_auth_functions(self) -> Dict[str, Union[AuthFunction,
                                                    ChainedAuthFunction]]:
        """
        Override, extend, and add authentication methods.

        Implement of: ckan.plugins.interfaces.IAuthFunctions
        SubMethod of: CkanSecurityPlugin
        """
        # type_ignore_reason: incomplete typing
        return super().get_auth_functions() | get_auth_methods()  # type: ignore

    def column_types(self, existing_types: Dict[str, Type[ColumnType]]):
        """
        Add custom column types to the DataStore via TableDesigner.

        Implement of: ckanext.tabledesigner.interfaces.IColumnTypes
        """
        return existing_types | get_datastore_column_types()

    def can_upload(self, resource_id: str) -> bool:
        """
        Whether or not a Resource can be loaded into the Datastore via XLoader.

        Implement of: ckanext.xloader.interfaces.IXloader
        """
        return dataset.can_xloader(resource_id)

    def update_dataset_citation_map(self, cite_data: DataDict,
                                    pkg_dict: DataDict) -> bool:
        """
        Updates the mapping for scientific notification for Datasets.

        Implement of: ckanext.citeproc.interfaces.ICiteProcMappings
        """
        dataset.update_citation_map(cite_data, pkg_dict)
        return False

    def update_resource_citation_map(self, cite_data: DataDict,
                                     pkg_dict: DataDict,
                                     res_dict: DataDict) -> bool:
        """
        Updates the mapping for scientific notification for Resources.

        Implement of: ckanext.citeproc.interfaces.ICiteProcMappings
        """
        dataset.update_citation_map(cite_data, pkg_dict)
        return False
