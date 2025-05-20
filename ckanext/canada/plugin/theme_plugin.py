from ckan.types import Callable, Any, Dict
from ckan.common import CKANConfig

import ckan.plugins as p
from ckan.lib.app_globals import set_app_global
from ckan.plugins.core import plugin_loaded

from ckanext.canada import helpers


@p.toolkit.blanket.config_declarations
class CanadaThemePlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)

    # IConfigurer
    def update_config(self, config: 'CKANConfig'):
        p.toolkit.add_template_directory(config, '../templates')
        p.toolkit.add_public_directory(config, '../public')
        p.toolkit.add_resource('../public/static/js', 'js')
        p.toolkit.add_resource('../assets/internal', 'canada_internal')
        p.toolkit.add_resource('../assets/datatables', 'canada_datatables')
        p.toolkit.add_resource('../assets/public', 'canada_public')
        p.toolkit.add_resource('../assets/invitation-manager', 'invitation_manager')
        # type_ignore_reason: jinja2 versioning
        set_app_global('is_registry',
                       bool(plugin_loaded('canada_internal')))  # type: ignore

        config['ckan.favicon'] = helpers.cdts_asset('/assets/favicon.ico')

    # ITemplateHelpers
    def get_helpers(self) -> Dict[str, Callable[..., Any]]:
        return dict((h, getattr(helpers, h)) for h in [
            # Registry
            'may_publish_datasets',
            'today',
            'date_format',
            'parse_release_date_facet',
            'is_ready_to_publish',
            'get_datapreview_recombinant',
            'recombinant_description_to_markup',
            'mail_to_with_params',
            'get_timeout_length',
            'canada_check_access',
            'get_user_email',
            'get_loader_status_badge',
            'validation_status',
            'is_user_locked',
            # Portal
            'user_organizations',
            'openness_score',
            'remove_duplicates',
            'get_license',
            'normalize_strip_accents',
            'portal_url',
            'adv_search_url',
            'adv_search_mlt_root',
            'ga4_id',
            'loop11_key',
            'contact_information',
            'show_openinfo_facets',
            'json_loads',
            'catalogue_last_update_date',
            'get_translated_t',
            'language_text_t',
            'get_datapreview',
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
        ])
