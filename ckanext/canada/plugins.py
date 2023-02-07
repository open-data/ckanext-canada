#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import os.path
import logging
import ckan.plugins as p
from ckan.lib.plugins import DefaultDatasetForm, DefaultTranslation
import ckan.lib.helpers as hlp
from ckan.logic import validators as logic_validators
from routes.mapper import SubMapper
from paste.reloader import watch_file

from ckan.plugins.toolkit import h, chained_action, ValidationError, ObjectNotFound, _, get_validator
import ckanapi
from ckan.lib.base import c

from ckanext.canada import validators
from ckanext.canada import logic
from ckanext.canada import auth
from ckanext.canada import helpers
from ckanext.canada import activity as act
from ckanext.canada import search_integration
from ckanext.xloader.interfaces import IXloader
import json

import ckan.lib.formatters as formatters
from webhelpers.html import literal
from flask import Blueprint
from ckanext.scheming.plugins import SchemingDatasetsPlugin
from ckanext.canada.views import (
    canada_views,
    CanadaDatasetEditView,
    CanadaResourceEditView,
    CanadaResourceCreateView
)

# XXX Monkey patch to work around libcloud/azure 400 error on get_container
try:
    import libcloud.common.azure
    libcloud.common.azure.API_VERSION = '2014-02-14'
except ImportError:
    pass

log = logging.getLogger(__name__)


class CanadaDatasetsPlugin(SchemingDatasetsPlugin):
    """
    Plugin for dataset and resource
    """
    p.implements(p.IDatasetForm, inherit=True)
    p.implements(p.IPackageController, inherit=True)

    #IDatasetForm
    def prepare_dataset_blueprint(self, package_type, blueprint):
        # type: (str,Blueprint) -> Blueprint
        blueprint.add_url_rule(
            u'/edit/<id>',
            endpoint='canada_edit',
            view_func=CanadaDatasetEditView.as_view(str(u'edit')),
            methods=['GET', 'POST']
        )
        return blueprint


    #IDatasetForm
    def prepare_resource_blueprint(self, package_type, blueprint):
        # type: (str,Blueprint) -> Blueprint
        blueprint.add_url_rule(
            u'/<resource_id>/edit',
            endpoint='canada_edit',
            view_func=CanadaResourceEditView.as_view(str(u'edit')),
            methods=['GET', 'POST']
        )
        blueprint.add_url_rule(
            u'/new',
            endpoint='canada_new',
            view_func=CanadaResourceCreateView.as_view(str(u'new')),
            methods=['GET', 'POST']
        )
        return blueprint


    # IPackageController
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
        from ckan.plugins.toolkit import c
        try:
            c.fields_grouped.pop('wbdisable', None)
        except Exception:
            pass

        return search_params


    # IPackageController
    def after_search(self, search_results, search_params):
        for result in search_results.get('results', []):
            for extra in result.get('extras', []):
                if extra.get('key') in ['title_fra', 'notes_fra']:
                    result[extra['key']] = extra['value']

        return search_results


    # IPackageController
    def before_index(self, data_dict):
        kw = json.loads(data_dict.get('extras_keywords', '{}'))
        data_dict['keywords'] = kw.get('en', [])
        data_dict['keywords_fra'] = kw.get('fr', kw.get('fr-t-en', []))
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

        try:
            geno = h.recombinant_get_geno(data_dict['type']) or {}
        except AttributeError:
            pass
        else:
            data_dict['portal_type'] = geno.get('portal_type', data_dict['type'])
            if 'collection' in geno:
                data_dict['collection'] = geno['collection']

        if 'fgp_viewer' in data_dict.get('display_flags', []):
            data_dict['fgp_viewer'] = 'map_view'

        titles = json.loads(data_dict.get('title_translated', '{}'))
        data_dict['title_fr'] = titles.get('fr', '')
        data_dict['title_string'] = titles.get('en', '')

        if data_dict['type'] == 'prop':
            status = data_dict.get('status')
            data_dict['status'] = status[-1]['reason'] if status else 'department_contacted'

        if data_dict.get('credit'):
            for cr in data_dict['credit']:
                cr.pop('__extras', None)

        return data_dict


    # IPackageController
    def after_create(self, context, data_dict):
        search_integration.add_to_search_index(data_dict['id'], in_bulk=False)
        return data_dict


    # IPackageController
    def after_update(self, context, data_dict):
        search_integration.add_to_search_index(data_dict['id'], in_bulk=False)
        return data_dict


    # IPackageController
    def after_delete(self, context, data_dict):
        search_integration.delete_from_search_index(data_dict['id'])
        return data_dict


class DataGCCAInternal(p.SingletonPlugin):
    """
    Plugin for internal version of data.gc.ca site, aka the "registry"
    This plugin requires the DataGCCAPublic and DataGCCAForms plugins
    """
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IResourceUrlChange)
    p.implements(p.IBlueprint)
    p.implements(IXloader)

    # IConfigurer
    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates/internal')
        p.toolkit.add_public_directory(config, 'internal/static')

        config.update({
            "ckan.user_list_limit": 250
        })
        # registry includes validation so use real validation presets
        config['scheming.presets'] = """
ckanext.scheming:presets.json
ckanext.fluent:presets.json
ckanext.canada:schemas/presets.yaml
""" + (
	"ckanext.validation:presets.json" if "validation" in config['ckan.plugins'] else
	"ckanext.canada:schemas/validation_placeholder_presets.yaml"
)


    # IBlueprint
    def get_blueprint(self):
        # type: () -> list[Blueprint]
        return [canada_views]


    # IRoutes
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
        # reset to regular delete controller for internal site
        map.connect(
            'dataset_delete',
            '/dataset/delete/{id}',
            controller='package',
            action='delete'
        )
        map.connect(
            'create_pd_record',
            '/create-pd-record/{owner_org}/{resource_name}',
            controller='ckanext.canada.controller:PDUpdateController',
            action='create_pd_record',
        )
        map.connect(
            'update_pd_record',
            '/update-pd-record/{owner_org}/{resource_name}/{pk}',
            controller='ckanext.canada.controller:PDUpdateController',
            action='update_pd_record',
        )
        map.connect('recombinant_type',
                    '/recombinant/{resource_name}',
                    action='type_redirect',
                    controller='ckanext.canada.controller:PDUpdateController')
        map.connect(
            'delete_datastore_table',
            '/dataset/{id}/delete-datastore-table/{resource_id}',
            controller='ckanext.canada.controller:CanadaDatastoreController',
            action='delete_datastore_table',
        )

        return map

    # IRoutes
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

    # IResourceUrlChange
    def notify(self, resource):
        p.toolkit.enqueue_job(fn=remove_outdated_resource_from_datastore, args=[resource.id])

    # ITemplateHelpers
    def get_helpers(self):
        return dict((h, getattr(helpers, h)) for h in [
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
        ])

    # IConfigurable
    def configure(self, config):
        # FIXME: monkey-patch datastore upsert_data
        from ckanext.datastore.backend import postgres as db
        original_upsert_data = db.upsert_data
        def patched_upsert_data(context, data_dict):
            logic.datastore_create_temp_user_table(context)
            try:
                return original_upsert_data(context, data_dict)
            except ValidationError as e:
                # reformat tab-delimited error as dict
                head, sep, rerr = e.error_dict.get('records', [''])[0].partition('\t')
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
                k: disabled_anon_action for k in [
                    'package_activity_list',
                    'recently_changed_packages_activity_list',
                    'dashboard_activity_list',
                    'changed_packages_activity_timestamp_since',
                ]
            },
            resource_view_update=resource_view_update_bilingual,
            resource_view_create=resource_view_create_bilingual,
        )

    # IXloader

    def can_upload(self, resource_id):

        # check if file is uploded
        try:
            res = p.toolkit.get_action(u'resource_show')({'ignore_auth': True},
                                                         {'id': resource_id})

            if res.get('url_type', None) != 'upload':
                log.error(
                    'Only uploaded resources can be added to the Data Store.')
                return False

        except ObjectNotFound:
            log.error('Resource %s does not exist.' % resource_id)
            return False

        # check if validation report exists
        try:
            validation = p.toolkit.get_action(u'resource_validation_show')(
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


@chained_action
def disabled_anon_action(up_func, context, data_dict):
    if context.get('user', 'visitor') in ('', 'visitor'):
        return []
    return up_func(context, data_dict)
disabled_anon_action.side_effect_free = True
disabled_anon_action.auth_audit_exempt = True  # XXX ought to be a better way...


@chained_action
def resource_view_create_bilingual(up_func, context, data_dict):
    from ckan.logic.schema import default_create_resource_view_schema_filtered
    # FIXME: assuming all resource views we used are filtered
    s = default_create_resource_view_schema_filtered()
    return up_func(
        dict(
            context,
            schema=dict(
                s,
                title=[get_validator('default')('View'), get_validator('unicode_safe')],
                title_fr=[get_validator('default')('Vue'), get_validator('unicode_safe')],
                description=[get_validator('default')(''), get_validator('unicode_safe')],
                description_fr=[get_validator('default')(''), get_validator('unicode_safe')],
            ),
        ),
        data_dict
    )

@chained_action
def resource_view_update_bilingual(up_func, context, data_dict):
    from ckan.logic.schema import (
        default_create_resource_view_schema_filtered,
        default_update_resource_view_schema_changes,
    )
    # FIXME: assuming all resource views we used are filtered
    s = default_create_resource_view_schema_filtered()
    s.update(default_update_resource_view_schema_changes())
    return up_func(
        dict(
            context,
            schema=dict(
                s,
                title_fr=list(s['title']),
                description_fr=list(s['description']),
            ),
        ),
        data_dict
    )


class DataGCCAPublic(p.SingletonPlugin, DefaultTranslation):
    """
    Plugin for public-facing version of Open Government site, aka the "portal"
    This plugin requires the DataGCCAForms plugin
    """
    p.implements(p.IConfigurer)
    p.implements(p.IAuthFunctions)
    p.implements(p.IFacets)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.ITranslation, inherit=True)
    p.implements(p.IMiddleware, inherit=True)
    p.implements(p.IActions)


    # DefaultTranslation, ITranslation
    def i18n_domain(self):
        return 'ckanext-canada'

    # IConfigurer
    def update_config(self, config):
        # add our templates
        p.toolkit.add_template_directory(config, 'templates/public')
        p.toolkit.add_public_directory(config, 'public')
        p.toolkit.add_resource('public/static/js', 'js')
        config['recombinant.definitions'] = """
ckanext.canada:tables/ati.yaml
ckanext.canada:tables/briefingt.yaml
ckanext.canada:tables/qpnotes.yaml
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
ckanext.canada:tables/service.yaml
ckanext.canada:tables/dac.yaml
ckanext.canada:tables/nap5.yaml
ckanext.canada:tables/experiment.yaml
ckanext.canada:tables/adminaircraft.yaml

"""
        config['ckan.search.show_all_types'] = True
        config['ckan.gravatar_default'] = 'disabled'
        config['search.facets.limit'] = 200  # because org list
        if 'validation' not in config.get('scheming.presets', ''):
            config['scheming.presets'] = """
ckanext.scheming:presets.json
ckanext.fluent:presets.json
ckanext.canada:schemas/presets.yaml
ckanext.canada:schemas/validation_placeholder_presets.yaml
"""
        config['scheming.dataset_schemas'] = """
ckanext.canada:schemas/dataset.yaml
ckanext.canada:schemas/info.yaml
ckanext.canada:schemas/prop.yaml
"""
        config['scheming.organization_schemas'] = 'ckanext.canada:schemas/organization.yaml'

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

        # monkey patch helpers.py pagination method
        hlp.Page.pager = _wet_pager
        hlp.SI_number_span = _SI_number_span_close

        hlp.build_nav_main = build_nav_main

        # migration from `canada_activity` and `ckanext-extendedactivity` - Aug 2022
        logic_validators.object_id_validators.update({
            'changed datastore': logic_validators.package_id_exists,
            'deleted datastore': logic_validators.package_id_exists,
        })

    # IFacets
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
            'jurisdiction': _('Jurisdiction'),
            'status': _('Suggestion Status'),
            })

        return facets_dict

    # IFacets
    #FIXME: remove `group_facets` method once issue https://github.com/ckan/ckan/issues/7017 is patched into <2.9
    def group_facets(self, facets_dict, group_type, package_type):
        ''' Update the facets_dict and return it. '''
        if group_type == 'organization':
            return self.dataset_facets(facets_dict, package_type)
        return facets_dict

    # IFacets
    def organization_facets(self, facets_dict, organization_type,
                            package_type):
        return self.dataset_facets(facets_dict, package_type)


    # ITemplateHelpers
    def get_helpers(self):
        return dict((h, getattr(helpers, h)) for h in [
            'user_organizations',
            'openness_score',
            'remove_duplicates',
            'get_license',
            'normalize_strip_accents',
            'portal_url',
            'adv_search_url',
            'googleanalytics_id',
            'loop11_key',
            'drupal_session_present',
            'fgp_url',
            'contact_information',
            'show_subject_facet',
            'show_fgp_facets',
            'show_openinfo_facets',
            'gravatar',
            'linked_gravatar',
            'linked_user',
            'json_loads',
            'catalogue_last_update_date',
            'get_translated_t',
            'language_text_t',
            'link_to_user',
            'get_datapreview',
            'iso_to_goctime',
            'geojson_to_wkt',
            'url_for_wet_theme',
            'url_for_wet',
            'wet_jquery_offline',
            'get_map_type',
            'adobe_analytics_login_required',
            'adobe_analytics_lang',
            'adobe_analytics_js',
            'mail_to_with_params',
        ])


    # IRoutes
    def before_map(self, map):
        map.connect(
            '/fgpv_vpgf/{pkg_id}',
            action='fgpv_vpgf',
            controller='ckanext.canada.controller:CanadaController'
        )
        with SubMapper(map, controller='ckanext.canada.controller:CanadaFeedController') as m:
            m.connect('/feeds/organization/{id}.atom', action='organization')
        map.connect(
            'general', '/feeds/dataset/{pkg_id}.atom',
            controller='ckanext.canada.controller:CanadaFeedController',
            action='dataset',
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
            '/api{ver:/3|}/action/{logic_function}',
            ver='/3',
            action='action',
            controller='ckanext.canada.controller:CanadaApiController',
            conditions={'method':['GET', 'POST']},
        )
        return map

    # IActions
    # `datastore_upsert` and `datastore_delete` migrated from `canada_activity` and `ckanext-extendedactivity` - Aug 2022
    def get_actions(self):
        return {
                'datastore_upsert': datastore_upsert,
                'datastore_delete': datastore_delete}

    # IAuthFunctions
    def get_auth_functions(self):
        return {
            'datastore_create': auth.datastore_create,
            'datastore_delete': auth.datastore_delete,
            'datastore_upsert': auth.datastore_upsert,
        }

    # IMiddleware

    def make_middleware(self, app, config):
        return LogExtraMiddleware(app, config)




class DataGCCAForms(p.SingletonPlugin, DefaultDatasetForm):
    """
    Plugin for dataset forms for Canada's metadata schema
    """
    p.implements(p.IActions)
    p.implements(p.IValidators, inherit=True)

    # IActions

    def get_actions(self):
        actions = logic.limit_api_logic()
        actions.update((h, getattr(logic, h)) for h in [
            'changed_packages_activity_timestamp_since',
            ])
        actions.update({k: disabled_anon_action for k in [
            'current_package_list_with_resources',
            'user_list',
            'user_activity_list',
            'member_list',
            #'user_show',  FIXME: required for password reset
            'package_autocomplete',
            'format_autocomplete',
            'user_autocomplete',
            'group_activity_list',
            'organization_activity_list',
            'group_package_show',
            ]})
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
            'licence_choices':
                validators.licence_choices,
            'string_safe':
                validators.string_safe,
            'string_safe_stop':
                validators.string_safe_stop,
            'json_string':
                validators.json_string,
            'json_string_has_en_fr_keys':
                validators.json_string_has_en_fr_keys,
            }


class LogExtraMiddleware(object):
    def __init__(self, app, config):
        self.app = app

    def __call__(self, environ, start_response):
        def _start_response(status, response_headers, exc_info=None):
            extra = []
            if c.user:
                log_extra = c.log_extra if hasattr(c, 'log_extra') else u''
                extra = [(
                    'X-LogExtra', u'user={uid} {extra}'.format(
                        uid=c.user,
                        extra=log_extra).encode('utf-8')
                    )
                ]

            return start_response(
                status,
                response_headers + extra,
                exc_info)

        return self.app(environ, _start_response)


@chained_action
def datastore_upsert(up_func, context, data_dict):
    lc = ckanapi.LocalCKAN(username=context['user'])
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
    if data_dict.get('url_type', None) == 'upload':
        return up_func(context, data_dict)

    lc = ckanapi.LocalCKAN(username=c.user)
    res_id = data_dict['id'] if 'id' in data_dict.keys() else data_dict['resource_id']
    res = lc.action.datastore_search(
        resource_id=res_id,
        filters=data_dict.get('filters'),
        limit=1,
    )

    result = up_func(context, data_dict)

    act.datastore_activity_create(context,
                                  {'count': res.get('total', 0),
                                   'activity_type': 'deleted datastore',
                                   'resource_id': res_id}
                                  )
    return result


def _wet_pager(self, *args, **kwargs):
    ## a custom pagination method, because CKAN doesn't expose the pagination to the templates,
    ## and instead hardcodes the pagination html in helpers.py

    kwargs.update(
        format=u"<ul class='pagination'>$link_previous ~2~ $link_next</ul>",
        symbol_previous=hlp._('Previous'), symbol_next=hlp._('Next'),
        curpage_attr={'class': 'active'}
    )

    return super(hlp.Page, self).pager(*args, **kwargs)

def _SI_number_span_close(number):
    ''' outputs a span with the number in SI unit eg 14700 -> 14.7k '''
    number = int(number)
    if number < 1000:
        output = literal('<span>')
    else:
        output = literal('<span title="' + formatters.localised_number(number) + '">')
    return output + formatters.localised_SI_number(number) + literal('</span>')


# Monkey Patched to inlude the 'list-group-item' class
# TODO: Clean up and convert to proper HTML templates
def build_nav_main(*args):
    ''' build a set of menu items.

    args: tuples of (menu type, title) eg ('login', _('Login'))
    outputs <li><a href="...">title</a></li>
    '''
    output = ''
    for item in args:
        menu_item, title = item[:2]
        if len(item) == 3 and not hlp.check_access(item[2]):
            continue
        output += hlp._make_menu_item(menu_item, title, class_='list-group-item')
    return output


def remove_outdated_resource_from_datastore(resource_id):
    from ckan import model
    context = {'model': model, 'ignore_auth': True}
    try:
        res = p.toolkit.get_action(u'resource_show')(context, {'id': resource_id})
    except ObjectNotFound:
        log.error('Resource %s does not exist.' % res['id'])
        return

    # remove outdated validation report for linked resources
    if res['url_type'] != 'upload' and h.validation_status(res['id']) != 'unknown':
        try:
            p.toolkit.get_action(u'resource_validation_delete')(
                context, {'resource_id': res['id']})
            log.info('Validation report deleted for resource %s' % res['id'])
        except ObjectNotFound:
            log.error('Validation report for resource %s does not exist' % res['id'])

    # remove outdated datastore table for linked resources
    if res['url_type'] != 'upload' and 'datastore_active' in res and res['datastore_active']:
        try:
            p.toolkit.get_action(u'datastore_delete')(
                context, {'resource_id': res['id'], 'force': True})
            log.info('Datastore table dropped for resource %s' % res['id'])
        except ObjectNotFound:
            log.error('Datastore table for resource %s does not exist' % res['id'])
