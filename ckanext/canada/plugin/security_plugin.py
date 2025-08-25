from typing import Any, Dict, List, Tuple, Optional
from ckan.types import Context, Validator, CKANApp
from ckan.common import CKANConfig

import random
import string

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
    p.implements(p.IMiddleware, inherit=True)

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
        config['ckan.auth.create_user_via_web'] = plugin_loaded(
            'canada_internal')  # /user/register view only on registry
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

    def make_middleware(self, app: CKANApp, config: 'CKANConfig') -> CKANApp:
        return CSPNonceMiddleware(app, config)


class CSPNonceMiddleware(object):
    def __init__(self, app: Any, config: 'CKANConfig'):
        self.config = config
        self.app = app

    def __call__(self, environ: Any, start_response: Any) -> Any:
        csp_nonce = ''.join(random.choices(
                string.ascii_letters + string.digits, k=22))
        environ['CSP_NONCE'] = csp_nonce
        csp_header = [
            ('Content-Security-Policy',
             self.config['ckanext.canada.content_security_policy'].replace(
                 '[[NONCE]]', csp_nonce))]

        def _start_response(status: str,
                            response_headers: List[Tuple[str, str]],
                            exc_info: Optional[Any] = None):
            return start_response(
                status,
                response_headers if self.config[
                    'ckanext.canada.disable_content_security_policy']
                else response_headers + csp_header,
                exc_info)

        return self.app(environ, _start_response)
