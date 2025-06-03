from typing import Any, Dict
from ckan.types import Context, Validator
from ckan.common import CKANConfig

import ckan.plugins as p
from ckan.plugins.core import plugin_loaded
from ckan.config.middleware.flask_app import csrf

from ckanext.datatablesview.blueprint import datatablesview
from ckanext.security.plugin import CkanSecurityPlugin
from ckanext.canada import validators


class CanadaSecurityPlugin(CkanSecurityPlugin):
    """
    Plugin for extra security
    """
    p.implements(p.IResourceController, inherit=True)
    p.implements(p.IValidators, inherit=True)
    p.implements(p.IConfigurer)

    def update_config(self, config: 'CKANConfig'):
        super(CanadaSecurityPlugin, self).update_config(config)
        # Disable auth settings
        config['ckan.auth.anon_create_dataset'] = False
        config['ckan.auth.create_unowned_dataset'] = False
        config['ckan.auth.create_dataset_if_not_in_organization'] = False
        config['ckan.auth.user_create_groups'] = False
        config['ckan.auth.user_create_organizations'] = False
        config['ckan.auth.create_user_via_api'] = config.get(
            'ckan.auth.create_user_via_api', False)  # allow setting in INI file
        # Enable auth settings
        config['ckan.auth.user_delete_groups'] = True
        config['ckan.auth.user_delete_organizations'] = True
        # NOTE: user register page for Registry is controlled by"
        #           - IP Intranet list
        #           - NGINX redirects
        config['ckan.auth.create_user_via_web'] = True
        # Set auth settings
        config['ckan.auth.roles_that_cascade_to_sub_groups'] = ['admin']

        csrf.exempt(datatablesview)

    def before_create(self, context: Context, resource: Dict[str, Any]):
        """
        Override before_create from CkanSecurityPlugin.
        Want to use the methods in scheming instead of before_create.
        """

    def before_update(self, context: Context,
                      current: Dict[str, Any], resource: Dict[str, Any]):
        """
        Override before_update from CkanSecurityPlugin.
        Want to use the methods in scheming instead of before_update.
        """

    def before_resource_create(self, context: Context, resource: Dict[str, Any]):
        """
        Override before_resource_create from CkanSecurityPlugin.
        Want to use the methods in scheming instead of before_resource_create.
        """

    def before_resource_update(self, context: Context,
                               current: Dict[str, Any], resource: Dict[str, Any]):
        """
        Override before_resource_update from CkanSecurityPlugin.
        Want to use the methods in scheming instead of before_resource_update.
        """

    def get_validators(self) -> Dict[str, Validator]:
        validators_dict = super(CanadaSecurityPlugin, self).get_validators() or {}
        return dict(
            validators_dict,
            canada_security_upload_type=validators.canada_security_upload_type,
            canada_security_upload_presence=validators.canada_security_upload_presence,
        )
