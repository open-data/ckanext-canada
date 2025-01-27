from typing import Dict, Union
from ckan.types import Action, ChainedAction, Validator

import ckan.plugins as p
from ckan.lib.plugins import DefaultDatasetForm

from ckanext.canada import validators
from ckanext.canada import logic


class CanadaFormsPlugin(p.SingletonPlugin, DefaultDatasetForm):
    """
    Plugin for dataset forms for Canada's metadata schema
    """
    p.implements(p.IActions)
    p.implements(p.IValidators, inherit=True)

    # IActions
    def get_actions(self) -> Dict[str, Union[Action, ChainedAction]]:
        actions = logic.limit_api_logic()
        actions.update((h, getattr(logic, h)) for h in [
            'changed_packages_activity_timestamp_since',
            'canada_guess_mimetype',
            ])
        actions.update({k: logic.disabled_anon_action for k in [
            'current_package_list_with_resources',
            'user_list',
            'user_activity_list',
            'member_list',
            # 'user_show',  FIXME: required for password reset
            'package_autocomplete',
            'format_autocomplete',
            'user_autocomplete',
            'group_activity_list',
            'organization_activity_list',
            'group_package_show',
            ]})
        # disable group & organization bulk actions as they do not support
        # IPackageController and IResourceController implementations.
        actions.update({k: logic.disabled_action for k in [
            'bulk_update_private',
            'bulk_update_public',
            'bulk_update_delete',
            '_bulk_update_dataset',]})
        return actions

    # IValidators
    def get_validators(self) -> Dict[str, Validator]:
        return {
            'canada_validate_generate_uuid':
                validators.canada_validate_generate_uuid,
            'canada_tags': validators.canada_tags,
            'geojson_validator': validators.geojson_validator,
            'email_validator': validators.email_validator,
            'protect_portal_release_date':
                validators.protect_portal_release_date,
            'canada_copy_from_org_name':
                validators.canada_copy_from_org_name,
            'canada_maintainer_email_default':
                validators.canada_maintainer_email_default,
            'user_read_only':
                validators.user_read_only,
            'user_read_only_json':
                validators.user_read_only_json,
            'canada_sort_prop_status':
                validators.canada_sort_prop_status,
            'no_future_date':
                validators.no_future_date,
            'canada_org_title_translated_save':
                validators.canada_org_title_translated_save,
            'canada_org_title_translated_output':
                validators.canada_org_title_translated_output,
            'protect_reporting_requirements':
                validators.protect_reporting_requirements,
            'ati_email_validate':
                validators.ati_email_validate,
            'isodate':
                validators.isodate,
            'string_safe':
                validators.string_safe,
            'string_safe_stop':
                validators.string_safe_stop,
            'json_string':
                validators.json_string,
            'json_string_has_en_fr_keys':
                validators.json_string_has_en_fr_keys,
            'canada_static_charset_tabledesigner':
                validators.canada_static_charset_tabledesigner,
            'canada_static_rtype_tabledesigner':
                validators.canada_static_rtype_tabledesigner,
            'canada_guess_resource_format':
                validators.canada_guess_resource_format,
            'canada_output_none':
                validators.canada_output_none,
            'protect_registry_access':
                validators.protect_registry_access,
            'digital_object_identifier':
                validators.digital_object_identifier,
            'limit_resources_per_dataset':
                validators.limit_resources_per_dataset,
            }
