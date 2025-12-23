import os
from flask import Blueprint

from typing import List
from ckan.types import Callable, Any, Dict, CKANApp
from ckan.common import CKANConfig

import ckan.plugins as p
from ckan.lib.plugins import DefaultTranslation

from ckanext.canada import helpers
from ckanext.canada.middleware import CSPNonceMiddleware
from ckanext.canada.view import canada_views


@p.toolkit.blanket.config_declarations
class CanadaThemePlugin(p.SingletonPlugin, DefaultTranslation):
    """
    Plugin for all of the themeing of the Open Government Canada Portal & Registry.

    See logic_plugin.py::CanadaLogicPlugin for actions,
    configurations, and other implementations.
    """
    p.implements(p.ITranslation)
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IMiddleware)
    p.implements(p.IBlueprint)

    @classmethod
    def i18n_domain(cls) -> str:
        """
        Sets the namespace for gettext.

        Implement of: ckan.plugins.interfaces.ITranslation
        Submethod of: ckan.lib.plugins.DefaultTranslation
        """
        return 'ckanext-canada'

    @classmethod
    def i18n_directory(cls) -> str:
        """
        Sets the directory where the plugin's translations files are located.

        Implement of: ckan.plugins.interfaces.ITranslation
        Submethod of: ckan.lib.plugins.DefaultTranslation
        """
        return os.path.join(os.path.dirname(str(__file__)), '../i18n')

    @classmethod
    def i18n_locales(cls) -> List[str]:
        """
        Sets the supported locales.

        Implement of: ckan.plugins.interfaces.ITranslation
        Submethod of: ckan.lib.plugins.DefaultTranslation
        """
        return ['en', 'fr']

    def update_config(self, config: 'CKANConfig'):
        """
        Add template directories and set initial configuration values.

        Implement of: ckan.plugins.interfaces.IConfigurer
        """
        p.toolkit.add_template_directory(config, '../templates')
        p.toolkit.add_public_directory(config, '../public')
        p.toolkit.add_resource('../assets/custom', 'canada_custom')
        p.toolkit.add_resource('../assets/datatables', 'canada_datatables')
        p.toolkit.add_resource('../assets/invitation-manager', 'invitation_manager')
        config['ckan.favicon'] = helpers.cdts_asset('/assets/favicon.ico')

    def get_helpers(self) -> Dict[str, Callable[..., Any]]:
        """
        Add available helper methods to the global h object. These methods
        are available via ckan.plugins.toolkit.h and inside Jinja2 templates.

        Implement of: ckan.plugins.interfaces.ITemplateHelpers
        """
        return dict((h, getattr(helpers, h)) for h in [
            'may_publish_datasets',
            'today',
            'date_format',
            'parse_release_date_facet',
            'is_ready_to_publish',
            'get_pd_datatable',
            'recombinant_description_to_markup',
            'mail_to_with_params',
            'get_timeout_length',
            'canada_check_access',
            'get_user_email',
            'get_loader_status_badge',
            'validation_status',
            'is_user_locked',
            'is_registry_domain',
            'linked_user',
            'user_organizations',
            'openness_score',
            'remove_duplicates',
            'get_license',
            'normalize_strip_accents',
            'portal_url',
            'adv_search_url',
            'adv_search_mlt_root',
            'ga4_id',
            'ga4_integrity',
            'loop11_key',
            'contact_information',
            'show_openinfo_facets',
            'json_loads',
            'catalogue_last_update_date',
            'get_translated_t',
            'language_text_t',
            'iso_to_goctime',
            'geojson_to_wkt',
            'cdts_asset',
            'get_map_type',
            'adobe_analytics_login_required',
            'adobe_analytics_lang',
            'adobe_analytics_js',
            'mail_to_with_params',
            'organization_member_count',
            'flash_notice',
            'flash_error',
            'flash_success',
            'adobe_analytics_creator',
            'resource_view_meta_title',
            'get_resource_view',
            'resource_view_type',
            'fgp_viewer_url',
            'date_field',
            'split_piped_bilingual_field',
            'search_filter_pill_link_label',
            'release_date_facet_start_year',
            'ckan_to_cdts_breadcrumbs',
            'available_purge_types',
            'operations_guide_link',
            'max_resources_per_dataset',
            'support_email_address',
            'default_open_email_address',
            'get_inline_script_nonce',
            'obfuscate_to_code_points',
            'mail_to',
        ])

    def make_middleware(self, app: CKANApp, config: 'CKANConfig') -> CKANApp:
        """
        Adds a Flask middleware object to the Flask app stack.

        Implement of: ckan.plugins.interfaces.IMiddleware
        """
        return CSPNonceMiddleware(app, config)

    def get_blueprint(self) -> List[Blueprint]:
        """
        Add Flask blueprint/view routes to the Flask app.

        Implement of: ckan.plugins.interfaces.IBlueprint
        """
        return [canada_views]
