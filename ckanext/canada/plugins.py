#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import os.path
from pylons.i18n import _
import ckan.plugins as p
from ckan.lib.plugins import DefaultDatasetForm
from ckan.logic import validators as logic_validators
from wcms import wcms_configure
from routes.mapper import SubMapper
from paste.reloader import watch_file

from ckantoolkit import h, chained_action
import ckanapi
from ckan.lib.base import c

from ckanext.canada.metadata_schema import schema_description
from ckanext.canada import validators
from ckanext.canada import logic
from ckanext.canada import helpers
from ckanext.canada import activity as act
from ckanext.extendedactivity.plugins import IActivity

import json


class DataGCCAInternal(p.SingletonPlugin):
    """
    Plugin for internal version of data.gc.ca site, aka the "registry"
    This plugin requires the DataGCCAPublic and DataGCCAForms plugins
    """
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IRoutes, inherit=True)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates/internal')
        p.toolkit.add_public_directory(config, 'internal/static')

        config.update({
            "ckan.user_list_limit": 2000
        })

    def before_map(self, map):
        map.connect(
            '/',
            action='home',
            controller='ckanext.canada.controller:CanadaController'
        )
        map.connect(
            '/links',
            action='links',
            controller='ckanext.canada.controller:CanadaController'
        )
        map.connect(
            '/menu',
            action='registry_menu',
            controller='ckanext.canada.controller:CanadaController'
        )
        map.connect(
            '/user/logged_in',
            action='logged_in',
            controller='ckanext.canada.controller:CanadaUserController'
        )
        map.connect(
            '/user/register',
            action='register',
            controller='ckanext.canada.controller:CanadaUserController'
        )
        map.connect(
            'user_reports',
            '/user/reports/{id}',
            action='reports',
            controller='ckanext.canada.controller:CanadaUserController',
            ckan_icon='bar-chart-o'
        )
        map.connect(
            'ckanadmin_listusers',
            '/ckan-admin',
            action='index',
            controller='user',
            ckan_icon='user'
        )
        map.connect(
            'ckanadmin_publish',
            '/ckan-admin/publish',
            action='search',
            controller='ckanext.canada.controller:CanadaAdminController',
            ckan_icon='cloud-upload'
        )
        map.connect(
            '/ckan_admin/publish_datasets',
            action='publish',
            conditions=dict(method=['POST']),
            controller='ckanext.canada.controller:CanadaAdminController'
        )
        map.connect(
            '/dataset/{id}/resource_edit/{resource_id}',
            action='resource_edit',
            controller='ckanext.canada.controller:CanadaDatasetController'
        )
        # reset to regular delete controller for internal site
        map.connect(
            'dataset_delete',
            '/dataset/delete/{id}',
            controller='package',
            action='delete'
        )
        map.connect(
            '/travela/{id}/{resource_id}',
            controller='ckanext.canada.controller:PDUpdateController',
            action='create_travela',
            conditions=dict(method=['POST']),
        )

        return map

    def after_map(self, map):
        mapper = SubMapper(
            map,
            controller='ckanext.canada.controller:CanadaController'
        )

        with mapper as m:
            m.connect('/guidelines', action='view_guidelines')
            m.connect('/help', action='view_help')
            m.connect(
                '/datatable/{resource_name}/{resource_id}',
                action='datatable'
            )
        return map

    def get_helpers(self):
        return dict((h, getattr(helpers, h)) for h in [
            'may_publish_datasets',
            'today',
            'date_format',
            'parse_release_date_facet',
            'is_ready_to_publish',
            'get_datapreview_recombinant',
            ])

    def configure(self, config):
        if 'ckan.drupal.url' in config:
            wcms_configure(config['ckan.drupal.url'])

        # FIXME: monkey-patch datastore upsert_data
        from ckanext.datastore import db
        original_upsert_data = db.upsert_data
        def patched_upsert_data(context, data_dict):
            logic.datastore_create_temp_user_table(context)
            return original_upsert_data(context, data_dict)
        if db.upsert_data.__name__ == 'upsert_data':
            db.upsert_data = patched_upsert_data


class DataGCCAPublic(p.SingletonPlugin):
    """
    Plugin for public-facing version of Open Government site, aka the "portal"
    This plugin requires the DataGCCAForms plugin
    """
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer)
    p.implements(p.IFacets)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IRoutes, inherit=True)

    def update_config(self, config):
        # add our templates
        p.toolkit.add_template_directory(config, 'templates/public')
        p.toolkit.add_public_directory(config, 'public')
        p.toolkit.add_resource('public/static/js', 'js')
        config['recombinant.definitions'] = """
ckanext.canada:tables/ati.yaml
ckanext.canada:tables/contracts.yaml
ckanext.canada:tables/contractsa.yaml
ckanext.canada:tables/grants.yaml
ckanext.canada:tables/hospitalityq.yaml
ckanext.canada:tables/reclassification.yaml
ckanext.canada:tables/travela.yaml
ckanext.canada:tables/travelq.yaml
ckanext.canada:tables/wrongdoing.yaml
ckanext.canada:tables/inventory.yaml
ckanext.canada:tables/consultations.yaml
"""
        config['ckan.search.show_all_types'] = True
        config['search.facets.limit'] = 200  # because org list
        config['scheming.presets'] = """
ckanext.scheming:presets.json
ckanext.fluent:presets.json
ckanext.canada:schemas/presets.yaml
"""
        config['scheming.dataset_schemas'] = """
ckanext.canada:schemas/dataset.yaml
ckanext.canada:schemas/info.yaml
"""

        # Enable our custom DCAT profile.
        config['ckanext.dcat.rdf.profile'] = 'canada_dcat'

        if 'ckan.i18n_directory' in config:
            # Reload when translaton files change, because I'm slowly going
            # insane.
            translations_dir = config['ckan.i18n_directory']
            if os.path.isdir(translations_dir):
                for folder, subs, files in os.walk(translations_dir):
                    for filename in files:
                        watch_file(os.path.join(folder, filename))

    def dataset_facets(self, facets_dict, package_type):
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
            'topic_category': _('Topic Categories'),
            'spatial_representation_type': _('Spatial Representation Type'),
            'fgp_viewer': _('Map Viewer'),
            'ready_to_publish': _('Record Status'),
            'imso_approval': _('IMSO Approval'),
            })

        return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):
        ''' Update the facets_dict and return it. '''
        return facets_dict

    def organization_facets(self, facets_dict, organization_type,
                            package_type):
        return self.dataset_facets(facets_dict, package_type)

    def get_helpers(self):
        return dict((h, getattr(helpers, h)) for h in [
            'user_organizations',
            'dataset_comments',
            'openness_score',
            'remove_duplicates',
            'get_license',
            'normalize_strip_accents',
            'dataset_rating',
            'dataset_comment_count',
            'portal_url',
            'googleanalytics_id',
            'drupal_session_present',
            'fgp_url',
            'contact_information',
            'show_subject_facet',
            'show_fgp_facets',
            'gravatar',
            'linked_gravatar',
            'linked_user',
            'json_loads',
            'catalogue_last_update_date'
            ])

    def before_map(self, map):
        map.connect(
            '/fgpv_vpgf/{pkg_id}',
            action='fgpv_vpgf',
            controller='ckanext.canada.controller:CanadaController'
        )
        map.connect(
            'organizations_index', '/organization',
            controller='ckanext.canada.controller:CanadaController',
            action='organization_index',
        )
        map.connect(
            'general', '/feeds/dataset.atom',
            controller='ckanext.canada.controller:CanadaFeedController',
            action='general',
        )
        map.connect(
            '/dataset/delete/{pkg_id}',
            controller='ckanext.canada.controller:CanadaController',
            action='package_delete'
        )
        map.connect(
            '/dataset/undelete/{pkg_id}',
            controller='ckanext.canada.controller:CanadaController',
            action='package_undelete'
        )
        map.connect(
            '/organization/autocomplete',
            action='organization_autocomplete',
            controller='ckanext.canada.controller:CanadaController',
        )
        map.connect(
            '/data-dictionary/{pd_file}',
            controller='ckanext.canada.controller:CanadaController',
            action='data_dictionary'
        )
        return map

    def configure(self, config):

        if ('ckan.drupal.url' in config):
            wcms_configure(config['ckan.drupal.url'])


class DataGCCAForms(p.SingletonPlugin, DefaultDatasetForm):
    """
    Plugin for dataset forms for Canada's metadata schema
    """
    p.implements(p.IConfigurable)
    p.implements(p.IActions)
    p.implements(p.IValidators, inherit=True)

    # IConfigurable

    def configure(self, config):
        jinja_globals = config['pylons.app_globals'].jinja_env.globals
        jinja_globals['schema_description'] = schema_description

    # IActions

    def get_actions(self):
        actions = logic.limit_api_logic()
        actions.update((h, getattr(logic, h)) for h in [
            'changed_packages_activity_list_since',
            ])
        return actions

    # IValidators

    def get_validators(self):
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
            'canada_non_related_required':
                validators.canada_non_related_required,
            'if_empty_set_to':
                validators.if_empty_set_to,
            }


class DataGCCAPackageController(p.SingletonPlugin):
    p.implements(p.IPackageController)

    def read(self, entity):
        pass

    def create(self, entity):
        pass

    def edit(self, entity):
        pass

    def authz_add_role(self, object_role):
        pass

    def authz_remove_role(self, object_role):
        pass

    def delete(self, entity):
        pass

    def before_search(self, search_params):
        # We're going to group portal_release_date into two bins - to today and
        # after today.
        search_params['facet.range'] = 'portal_release_date'
        search_params['facet.range.start'] = 'NOW/DAY-100YEARS'
        search_params['facet.range.end'] = 'NOW/DAY+100YEARS'
        search_params['facet.range.gap'] = '+100YEARS'

        # FIXME: so terrible. hack out WET4 wbdisable parameter
        try:
            search_params['fq'] = search_params['fq'].replace(
                'wbdisable:"true"', '').replace(
                'wbdisable:"false"', '')
        except Exception:
            pass
        from pylons import c
        try:
            c.fields_grouped.pop('wbdisable', None)
        except Exception:
            pass

        return search_params

    def after_search(self, search_results, search_params):
        for result in search_results.get('results', []):
            for extra in result.get('extras', []):
                if extra.get('key') in ['title_fra', 'notes_fra']:
                    result[extra['key']] = extra['value']

        return search_results

    def before_index(self, data_dict):
        kw = json.loads(data_dict.get('extras_keywords', '{}'))
        data_dict['keywords'] = kw.get('en', [])
        data_dict['keywords_fra'] = kw.get('fr', [])
        data_dict['catalog_type'] = data_dict.get('type', '')

        data_dict['subject'] = json.loads(data_dict.get('subject', '[]'))
        data_dict['topic_category'] = json.loads(data_dict.get(
            'topic_category', '[]'))
        try:
            data_dict['spatial_representation_type'] = json.loads(
                data_dict.get('spatial_representation_type')
            )
        except (TypeError, ValueError):
            data_dict['spatial_representation_type'] = []

        if data_dict.get('portal_release_date'):
            data_dict.pop('ready_to_publish', None)
        elif data_dict.get('ready_to_publish') == 'true':
            data_dict['ready_to_publish'] = 'true'
        else:
            data_dict['ready_to_publish'] = 'false'

        geno = h.recombinant_get_geno(data_dict['type']) or {}
        data_dict['portal_type'] = geno.get('portal_type', data_dict['type'])
        if 'collection' in geno:
            data_dict['collection'] = geno['collection']

        if 'fgp_viewer' in data_dict.get('display_flags', []):
            data_dict['fgp_viewer'] = 'map_view'

        titles = json.loads(data_dict.get('title_translated', '{}'))
        data_dict['title_fr'] = titles.get('fr', '')
        data_dict['title_string'] = titles.get('en', '')
        return data_dict

    def before_view(self, pkg_dict):
        return pkg_dict

    def after_create(self, context, data_dict):
        return data_dict

    def after_update(self, context, data_dict):
        # FIXME: flash_success makes no sense if this was an API call
        # consider moving this to an overridden controller method instead
        if context.get('allow_state_change') and data_dict.get(
                'state') == 'active':
            h.flash_success(
                _("Your record %s has been saved.")
                % data_dict['id']
            )
        return data_dict

    def after_delete(self, context, data_dict):
        return data_dict

    def after_show(self, context, data_dict):
        return data_dict

    def update_facet_titles(self, facet_titles):
        return facet_titles


@chained_action
def datastore_upsert(up_func, context, data_dict):
    lc = ckanapi.LocalCKAN(username=c.user)
    res_data = lc.action.datastore_search(
        resource_id=data_dict['resource_id'],
        filters={},
        limit=1,
    )
    count = res_data.get('total', 0)
    result = up_func(context, data_dict)

    res_data = lc.action.datastore_search(
        resource_id=data_dict['resource_id'],
        filters={},
        limit=1,
    )
    count = res_data.get('total', 0) - count

    act.datastore_activity_create(context, {'count':count,
                                            'activity_type': 'changed datastore',
                                            'resource_id': data_dict['resource_id']}
                                  )
    return result


@chained_action
def datastore_delete(up_func, context, data_dict):
    lc = ckanapi.LocalCKAN(username=c.user)
    res = lc.action.datastore_search(
        resource_id=data_dict['resource_id'],
        filters=data_dict['filters'],
        limit=1,
    )
    result = up_func(context, data_dict)
    act.datastore_activity_create(context,
                                  {'count':res.get('total', 0),
                                   'activity_type': 'deleted datastore',
                                   'resource_id': data_dict['resource_id']}
                                  )
    return result


class CanadaActivity(p.SingletonPlugin):
    p.implements(p.IActions)
    p.implements(IActivity)

    def get_actions(self):
        return ({'datastore_upsert':datastore_upsert,
                'datastore_delete': datastore_delete})

    def string_icons(self, string_icons):
        string_icons.update({'deleted datastore': 'file',
                             'changed datastore': 'file'})

    def snippet_functions(self, snippet_functions):
        snippet_functions.update({'datastore': act.get_snippet_datastore,
                                  'datastore_detail':act.get_snippet_datastore_detail})

    def string_functions(self, string_functions):
        string_functions.update({'changed datastore':
                                 act.activity_stream_string_changed_datastore,})
        string_functions.update({'deleted datastore':
                                 act.activity_stream_string_deleted_datastore,})

    def actions_obj_id_validator(self, obj_id_validators):
        obj_id_validators.update({
            'changed datastore': logic_validators.package_id_exists,
            'deleted datastore': logic_validators.package_id_exists,
                })
