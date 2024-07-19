#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import re
from flask import has_request_context
import ckan.plugins as p
from ckan.lib.plugins import DefaultDatasetForm, DefaultTranslation
import ckan.lib.helpers as hlp
from ckan.logic import validators as logic_validators
from ckanext.datastore.interfaces import IDataDictionaryForm

from ckan.lib.app_globals import set_app_global
from ckan.plugins.core import plugin_loaded

from ckan.plugins.toolkit import (
    g,
    h,
    chained_action,
    ValidationError,
    ObjectNotFound,
    _,
    get_validator,
    request
)

from ckanext.canada import validators
from ckanext.canada import logic
from ckanext.canada import auth
from ckanext.canada import helpers
from ckanext.canada import cli
from ckanext.canada.pd import get_commands as get_pd_commands
from ckanext.canada import activity as act
# type_ignore_reason: importing to proc decorators
from ckanext.canada import checks  # type: ignore
from ckanext.canada import column_types as coltypes
from ckanext.tabledesigner.interfaces import IColumnTypes
from ckanext.xloader.interfaces import IXloader
import json

import ckan.lib.formatters as formatters
from flask import Blueprint
from ckanext.scheming.plugins import SchemingDatasetsPlugin
from ckanext.security.plugin import CkanSecurityPlugin
from ckanext.canada.view import (
    canada_views,
    CanadaDatasetEditView,
    CanadaDatasetCreateView,
    CanadaResourceEditView,
    CanadaResourceCreateView,
    canada_search,
    canada_prevent_pd_views,
    _get_package_type_from_dict
)

# XXX Monkey patch to work around libcloud/azure 400 error on get_container
try:
    import libcloud.common.azure
    libcloud.common.azure.API_VERSION = '2014-02-14'
except ImportError:
    pass

log = logging.getLogger(__name__)
fq_portal_release_date_match = re.compile(r"(portal_release_date:\"\[.*\]\")")


class CanadaThemePlugin(p.SingletonPlugin):

    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)

    # IConfigurer
    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates')
        p.toolkit.add_public_directory(config, 'public')
        p.toolkit.add_resource('public/static/js', 'js')
        p.toolkit.add_resource('assets/internal', 'canada_internal')
        p.toolkit.add_resource('assets/datatables', 'canada_datatables')
        p.toolkit.add_resource('assets/public', 'canada_public')
        p.toolkit.add_resource('assets/invitation-manager', 'invitation_manager')
        set_app_global('is_registry', plugin_loaded('canada_internal'))

        config['ckan.favicon'] = helpers.cdts_asset('/assets/favicon.ico')

    # ITemplateHelpers
    def get_helpers(self):
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
            'drupal_session_present',
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
        ])


class CanadaSecurityPlugin(CkanSecurityPlugin):
    """
    Plugin for extra security
    """
    p.implements(p.IResourceController, inherit=True)
    p.implements(p.IValidators, inherit=True)
    p.implements(p.IConfigurer)

    def update_config(self, config):
        super(CanadaSecurityPlugin, self).update_config(config)
        # Disable auth settings
        config['ckan.auth.anon_create_dataset'] = False
        config['ckan.auth.create_unowned_dataset'] = False
        config['ckan.auth.create_dataset_if_not_in_organization'] = False
        config['ckan.auth.user_create_groups'] = False
        config['ckan.auth.user_create_organizations'] = False
        config['ckan.auth.create_user_via_api'] = config.get('ckan.auth.create_user_via_api', False)  # allow setting in INI file
        # Enable auth settings
        config['ckan.auth.user_delete_groups'] = True
        config['ckan.auth.user_delete_organizations'] = True
        config['ckan.auth.create_user_via_web'] = plugin_loaded('canada_internal')  # /user/register view only on registry
        # Set auth settings
        config['ckan.auth.roles_that_cascade_to_sub_groups'] = 'admin'

    def before_create(self, context, resource):
        """
        Override before_create from CkanSecurityPlugin.
        Want to use the methods in scheming instead of before_create.
        """

    def before_update(self, context, current, resource):
        """
        Override before_update from CkanSecurityPlugin.
        Want to use the methods in scheming instead of before_update.
        """

    def get_validators(self):
        validators_dict = super(CanadaSecurityPlugin, self).get_validators() or {}
        return dict(
            validators_dict,
            canada_security_upload_type=validators.canada_security_upload_type,
            canada_security_upload_presence=validators.canada_security_upload_presence,
        )


class CanadaDatasetsPlugin(SchemingDatasetsPlugin):
    """
    Plugin for dataset and resource
    """
    p.implements(p.IDatasetForm, inherit=True)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.IBlueprint)
    p.implements(IDataDictionaryForm, inherit=True)

    try:
        from ckanext.validation.interfaces import IDataValidation
    except ImportError:
        log.warn('failed to import ckanext-validation interface')
    else:
        p.implements(IDataValidation, inherit=True)


    # IBlueprint
    def get_blueprint(self):
        """
        Prevents all Core Dataset and Resources Views
        for all the PD types. Will type_redirect them
        to the pd_type. Will allow /<pd_type>/activity
        """
        # type: () -> list[Blueprint]
        blueprints = []
        for pd_type in h.recombinant_get_types():
            blueprint = Blueprint(
                u'canada_%s' % pd_type,
                __name__,
                url_prefix=u'/%s' % pd_type,
                url_defaults={u'package_type': pd_type})
            blueprint.add_url_rule(
                u'/',
                endpoint='canada_search_%s' % pd_type,
                view_func=canada_search,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/<path:uri>',
                endpoint='canada_prevent_%s' % pd_type,
                view_func=canada_prevent_pd_views,
                methods=['GET', 'POST']
            )
            blueprints.append(blueprint)
        return blueprints


    def _redirect_pd_dataset_endpoints(blueprint):
        """
        Runs before request for /dataset and /dataset/<pkg id>/resource

        Checks if the actual package type is a PD type and redirects it.
        """
        if has_request_context() and hasattr(request, 'view_args'):
            id = request.view_args.get('id')
            if not id:
                return
            package_type = request.view_args.get('package_type')
            package_type = _get_package_type_from_dict(id, package_type)
            if package_type in h.recombinant_get_types():
                return h.redirect_to('canada.type_redirect',
                                        resource_name=package_type)


    #IDatasetForm
    def prepare_dataset_blueprint(self, package_type, blueprint):
        # type: (str,Blueprint) -> Blueprint
        blueprint.add_url_rule(
            u'/edit/<id>',
            endpoint='canada_edit_%s' % package_type,
            view_func=CanadaDatasetEditView.as_view(str(u'edit')),
            methods=['GET', 'POST']
        )
        blueprint.add_url_rule(
            u'/new',
            endpoint='canada_new_%s' % package_type,
            view_func=CanadaDatasetCreateView.as_view(str(u'new')),
            methods=['GET', 'POST']
        )
        blueprint.add_url_rule(
            u'/',
            endpoint='canada_search_%s' % package_type,
            view_func=canada_search,
            methods=['GET'],
            strict_slashes=False
        )
        # redirect PD endpoints accessed from /dataset/<pd pkg id>
        blueprint.before_request(self._redirect_pd_dataset_endpoints)
        return blueprint


    #IDatasetForm
    def prepare_resource_blueprint(self, package_type, blueprint):
        # type: (str,Blueprint) -> Blueprint
        blueprint.add_url_rule(
            u'/<resource_id>/edit',
            endpoint='canada_resource_edit_%s' % package_type,
            view_func=CanadaResourceEditView.as_view(str(u'edit')),
            methods=['GET', 'POST']
        )
        blueprint.add_url_rule(
            u'/new',
            endpoint='canada_resource_new_%s' % package_type,
            view_func=CanadaResourceCreateView.as_view(str(u'new')),
            methods=['GET', 'POST']
        )
        # redirect PD endpoints accessed from /dataset/<pd pkg id>/resource
        blueprint.before_request(self._redirect_pd_dataset_endpoints)
        return blueprint

    # IDataValidation

    def can_validate(self, context, resource):
        """
        Only uploaded resources are allowed to be validated
        """
        return resource.get(u'url_type') == u'upload'


    # IPackageController
    def before_search(self, search_params):
        # We're going to group portal_release_date into two bins - to today and
        # after today.
        search_params['facet.range'] = 'portal_release_date'
        search_params['facet.range.start'] = 'NOW/DAY-%sYEARS' % helpers.RELEASE_DATE_FACET_STEP
        search_params['facet.range.end'] = 'NOW/DAY+%sYEARS' % helpers.RELEASE_DATE_FACET_STEP
        search_params['facet.range.gap'] = '+%sYEARS' % helpers.RELEASE_DATE_FACET_STEP

        # FIXME: so terrible. hack out WET4 wbdisable parameter
        try:
            search_params['fq'] = search_params['fq'].replace(
                'wbdisable:"true"', '').replace(
                'wbdisable:"false"', '')
        except Exception:
            pass

        try:
            g.fields_grouped.pop('wbdisable', None)
        except Exception:
            pass

        # search extras for ckan-admin/publish route.
        # we only want to show ready to publish,
        # approved datasets without a release date.
        if has_request_context() and 'ckan-admin/publish' in request.url:
            search_params['extras']['ready_to_publish'] = u'true'
            search_params['extras']['imso_approval'] = u'true'
            search_params['fq'] += '+ready_to_publish:"true", +imso_approval:"true", -portal_release_date:*'

        # CKAN Core search view wraps all fq values with double quotes.
        # We need to remove double quotes from the portal_release_date queries.
        if 'fq' in search_params:
            for release_date_query in re.findall(fq_portal_release_date_match, search_params['fq']):
                search_params['fq'] = search_params['fq'].replace(release_date_query, release_date_query.replace('"', ''))

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

        # need to keep fgp_viewer in the index for Advanced Search App
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

    # IDataDictionaryForm

    def update_datastore_info_field(self, field, plugin_data):
        if 'info' or '_info' in plugin_data and 'info' not in field:
            if 'info' in plugin_data:
                field['info'] = plugin_data.get('info', {})
            elif '_info' in plugin_data:
                field['info'] = plugin_data.get('_info', {})
        return field


class DataGCCAInternal(p.SingletonPlugin):
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
        # registry includes validation so use real validation presets
        config['scheming.presets'] = """
ckanext.scheming:presets.json
ckanext.fluent:presets.json
ckanext.canada:schemas/presets.yaml
""" + (
	"ckanext.validation:presets.json" if "validation" in config['ckan.plugins'] else
	"ckanext.canada:schemas/validation_placeholder_presets.yaml"
)

        # Include private datasets in Feeds
        config['ckan.feeds.include_private'] = True


    # IConfigurable
    def configure(self, config):
        # FIXME: monkey-patch datastore upsert_data
        from ckanext.datastore.backend import postgres as db
        original_upsert_data = db.upsert_data
        def patched_upsert_data(context, data_dict):
            with logic.datastore_create_temp_user_table(context):
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
            datastore_run_triggers=logic.canada_datastore_run_triggers,
        )

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            'group_list': auth.group_list,
            'group_show': auth.group_show,
            'organization_list': auth.organization_list,
            'organization_show': auth.organization_show,
        }

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
    if not context.get('ignore_auth', False) and context.get('user', 'visitor') in ('', 'visitor'):
        return []
    return up_func(context, data_dict)
disabled_anon_action.side_effect_free = True
disabled_anon_action.auth_audit_exempt = True


def _disabled_action(context, data_dict):
    """
    Raises a NotFound exception to disable a logic action method.
    """
    raise ObjectNotFound
_disabled_action.side_effect_free = True
_disabled_action.auth_audit_exempt = True


@chained_action
def resource_view_create_bilingual(up_func, context, data_dict):
    from ckan.logic.schema import default_create_resource_view_schema_filtered
    # assuming all resource views we used are filtered
    # filter_fields and filter_values have ignore_missing validator
    # so using the filtered schema should be fine here.
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
    # assuming all resource views we used are filtered
    # filter_fields and filter_values have ignore_missing validator
    # so using the filtered schema should be fine here.
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
    p.implements(p.ITranslation, inherit=True)
    p.implements(p.IMiddleware, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IClick)
    p.implements(IColumnTypes)
    p.implements(p.IBlueprint)

    # DefaultTranslation, ITranslation
    def i18n_domain(self):
        return 'ckanext-canada'

    # IConfigurer
    def update_config(self, config):
        config['ckan.auth.public_user_details'] = False
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

        # Pretty output for Feeds
        config['ckan.feeds.pretty'] = True

        # Enable our custom DCAT profile.
        config['ckanext.dcat.rdf.profiles'] = 'euro_dcat_ap_2'

        # Enable license restriction
        config['ckan.dataset.restrict_license_choices'] = True

        # monkey patch helpers.py pagination method
        hlp.Page.pager = _wet_pager
        hlp.SI_number_span = _SI_number_span_close

        hlp.build_nav_main = build_nav_main

        # migration from `canada_activity` and `ckanext-extendedactivity` - Aug 2022
        # migrated from `ckan` canada fork for resource view activities - Jan 2024
        logic_validators.object_id_validators.update({
            'new resource view': logic_validators.package_id_exists,
            'changed resource view': logic_validators.package_id_exists,
            'deleted resource view': logic_validators.package_id_exists,
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

    # IActions
    def get_actions(self):
        return {
                'recently_changed_packages_activity_list': act.recently_changed_packages_activity_list,  #TODO: Remove this action override in CKAN 2.10 upgrade
                'resource_view_show': logic.canada_resource_view_show,
                'resource_view_list': logic.canada_resource_view_list,
                'job_list': logic.canada_job_list,
                'registry_jobs_running': logic.registry_jobs_running,
               }

    # IAuthFunctions
    def get_auth_functions(self):
        return {
            'datastore_create': auth.datastore_create,
            'datastore_delete': auth.datastore_delete,
            'datastore_upsert': auth.datastore_upsert,
            'view_org_members': auth.view_org_members,
            'registry_jobs_running': auth.registry_jobs_running,
        }

    # IMiddleware

    def make_middleware(self, app, config):
        return LogExtraMiddleware(app, config)

    # IClick

    def get_commands(self):
        return [cli.get_commands(), get_pd_commands()]

    # IColumnTypes

    def column_types(self, existing_types):
        return dict(
            existing_types,
            province=coltypes.Province,
            crabusnum=coltypes.CRABusinessNumber,
        )

    # IBlueprint
    def get_blueprint(self):
        # type: () -> list[Blueprint]
        return [canada_views]


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
            'canada_guess_mimetype',
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
        # disable group & organization bulk actions as they do not support
        # IPackageController and IResourceController implementations.
        actions.update({k: _disabled_action for k in [
            'bulk_update_private',
            'bulk_update_public',
            'bulk_update_delete',
            '_bulk_update_dataset',]})
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
            }


class LogExtraMiddleware(object):
    def __init__(self, app, config):
        self.app = app

    def __call__(self, environ, start_response):
        def _start_response(status, response_headers, exc_info=None):
            extra = []
            try:
                contextual_user = g.user
            except (TypeError, RuntimeError, AttributeError):
                contextual_user = None
            if contextual_user:
                log_extra = g.log_extra if hasattr(g, 'log_extra') else ''
                #FIXME: make sure username special chars are handled
                # the values in the tuple HAVE to be str types.
                extra = [('X-LogExtra', f'user={contextual_user} {log_extra}')]

            return start_response(
                status,
                response_headers + extra,
                exc_info)

        return self.app(environ, _start_response)


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
        output = h.literal('<span>')
    else:
        output = h.literal('<span title="' + formatters.localised_number(number) + '">')
    return output + formatters.localised_SI_number(number) + h.literal('</span>')


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

