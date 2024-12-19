import logging
from urllib.parse import urlsplit
from frictionless import system

import ckan.plugins as p
from ckan.plugins.toolkit import ValidationError, ObjectNotFound

from ckanext.datastore.backend import postgres as db
from ckanext.xloader.interfaces import IXloader
from ckanext.canada.plugin import CanadaValidationPlugin
from ckanext.canada import logic
from ckanext.canada import auth


log = logging.getLogger(__name__)


class CanadaInternalPlugin(p.SingletonPlugin):
    """
    Plugin for internal version of data.gc.ca site, aka the "registry"
    This plugin requires the DataGCCAPublic and DataGCCAForms plugins
    """
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.IActions)
    p.implements(IXloader, inherit=True)
    p.implements(p.IAuthFunctions)

    # IConfigurer
    def update_config(self, config):
        config.update({
            "ckan.user_list_limit": 250
        })

        # CKAN 2.10 plugin loading does not allow us to set the schema
        # files in update_config in a way that the load order will work fully.
        scheming_presets = config.get('scheming.presets', '')
        assert 'ckanext.scheming:presets.json' in scheming_presets
        assert 'ckanext.fluent:presets.json' in scheming_presets
        assert 'ckanext.canada:schemas/presets.yaml' in scheming_presets
        assert 'ckanext.validation:presets.json' in scheming_presets

        # Include private datasets in Feeds
        config['ckan.feeds.include_private'] = True

    # IConfigurable
    def configure(self, config):
        # FIXME: monkey-patch datastore upsert_data
        original_upsert_data = db.upsert_data

        def patched_upsert_data(context, data_dict):
            with logic.datastore_create_temp_user_table(context):
                try:
                    return original_upsert_data(context, data_dict)
                except ValidationError as e:
                    # reformat tab-delimited error as dict
                    head, sep, rerr = e.error_dict.get(
                        'records', [''])[0].partition('\t')
                    rerr = rerr.rstrip('\n')
                    if head == 'TAB-DELIMITED' and sep:
                        out = {}
                        it = iter(rerr.split('\t'))
                        for key, error in zip(it, it):
                            out.setdefault(key, []).append(error)
                        e.error_dict['records'] = [out]
                    raise e
        if db.upsert_data.__name__ == 'upsert_data':
            db.upsert_data = patched_upsert_data

        # register custom frictionless plugin
        system.register('canada-validation', CanadaValidationPlugin())

    # IPackageController
    def create(self, pkg):
        """
        All datasets on registry should now be marked private
        """
        pkg.private = True

    # IPackageController
    def edit(self, pkg):
        """
        All datasets on registry should now be marked private
        """
        pkg.private = True

    # IActions
    def get_actions(self):
        return dict(
            {
                k: logic.disabled_anon_action for k in [
                    'package_activity_list',
                    'recently_changed_packages_activity_list',
                    'dashboard_activity_list',
                    'changed_packages_activity_timestamp_since',
                ]
            },
            resource_view_update=logic.resource_view_update_bilingual,
            resource_view_create=logic.resource_view_create_bilingual,
            datastore_run_triggers=logic.canada_datastore_run_triggers,
            portal_sync_info=logic.portal_sync_info,
            list_out_of_sync_packages=logic.list_out_of_sync_packages,
        )

    # IAuthFunctions
    def get_auth_functions(self):
        return {
            'group_list': auth.group_list,
            'group_show': auth.group_show,
            'organization_list': auth.organization_list,
            'organization_show': auth.organization_show,
            'portal_sync_info': auth.portal_sync_info,
            'list_out_of_sync_packages': auth.list_out_of_sync_packages,
        }

    # IXloader
    def can_upload(self, resource_id):
        """
        Only uploaded resources are allowed to be xloadered, or allowed domain sources.
        """

        # check if file is uploded
        try:
            res = p.toolkit.get_action('resource_show')(
                {'ignore_auth': True}, {'id': resource_id})

            if (
              res.get('url_type') != 'upload' and
              res.get('url_type') != '' and
              res.get('url_type') is not None):
                log.debug(
                    'Only uploaded resources and allowed domain '
                    'sources can be added to the Data Store.')
                return False

            if not res.get('url_type'):
                allowed_domains = p.toolkit.config.get(
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
            validation = p.toolkit.get_action('resource_validation_show')(
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
