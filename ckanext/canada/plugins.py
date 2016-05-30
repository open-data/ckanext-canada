from pylons.i18n import _
import ckan.plugins as p
from ckan.lib.base import render, h
from ckan.lib.plugins import DefaultDatasetForm
from ckan.logic.action import create
from wcms import wcms_configure
from routes.mapper import SubMapper
from logging import getLogger
from ckanext.canada.metadata_schema import schema_description
from ckanext.canada.validators import (
    if_empty_generate_uuid,
    canada_tags,
    geojson_validator,
    protect_portal_release_date
)
from ckanext.canada import logic
from ckanext.canada import helpers

import json

# Ugly monkey patch to let us hook into the user_create action

ckan_user_create = create.user_create
ckan_user_create_dict = {}


def notify_ckan_user_create(context, data_dict):
    """
    Send an e-mail notification about new users that register on the site to
    the configured recipient
    @param context: standard context object
    @param data_dict: dictionary with field values from the user registration
                      form.
    @raise:
    """

    user = ckan_user_create(context, data_dict)
    if not ckan_user_create_dict:
        return user

    import ckan.lib.mailer

    try:
        if ckan_user_create_dict['email_address']:
            new_email = data_dict['email'].strip()
            new_fullname = data_dict['fullname'].strip()
            new_username = data_dict['name'].strip()
            new_phoneno = data_dict['phoneno'].strip()
            new_dept = data_dict['department'].strip()

            xtra_vars = {
                'email': new_email,
                'fullname': new_fullname,
                'username': new_username,
                'phoneno': new_phoneno,
                'dept': new_dept
            }
            ckan.lib.mailer.mail_recipient(
                ckan_user_create_dict['email_name'],
                ckan_user_create_dict['email_address'],
                (
                    u'New data.gc.ca Registry Account Created / Nouveau compte'
                    u' cr\u00e9\u00e9 dans le registre de Gouvernement ouvert',
                ),
                render(
                    'user/new_user_email.html',
                    extra_vars=xtra_vars
                )
            )
    except ckan.lib.mailer.MailerException as m:
        log = getLogger('ckanext')
        log.error(m.message)

    return user


class DataGCCAInternal(p.SingletonPlugin):
    """
    Plugin for internal version of data.gc.ca site, aka the "registry"
    This plugin requires the DataGCCAPublic and DataGCCAForms plugins
    """
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer)
    p.implements(p.IActions)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IRoutes, inherit=True)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates/internal')

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
            ckan_icon='bar-chart'
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
        return map

    def after_map(self, map):
        mapper = SubMapper(
            map,
            controller='ckanext.canada.controller:CanadaController'
        )

        with mapper as m:
            m.connect('/guidelines', action='view_guidelines')
            m.connect('/help', action='view_help')
            m.connect('/datatable/{resource_id}', action='datatable')

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

        if 'canada.notification_new_user_email' in config:
            ckan_user_create_dict['email_address'] = config[
                'canada.notification_new_user_email'
            ]
            if 'canada.notification_new_user_name' in config:
                ckan_user_create_dict['email_name'] = config[
                    'canada.notification_new_user_name'
                ]
            else:
                ckan_user_create_dict['email_name'] = config[
                    'canada.notification_new_user_email'
                ]

    def get_actions(self):
        return {'user_create': notify_ckan_user_create}


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
ckanext.canada:tables/grants.yaml
ckanext.canada:tables/hospitalityq.yaml
ckanext.canada:tables/reclassification.yaml
ckanext.canada:tables/travela.yaml
ckanext.canada:tables/travelq.yaml
ckanext.canada:tables/wrongdoing.yaml
"""
        config['ckan.search.show_all_types'] = True
        config['scheming.presets'] = """
ckanext.scheming:presets.json
ckanext.fluent:presets.json
ckanext.canada:schemas/presets.yaml
"""
        config['scheming.dataset_schemas'] = """
ckanext.canada:schemas/dataset.yaml
ckanext.canada:schemas/info.yaml
"""

    def dataset_facets(self, facets_dict, package_type):
        ''' Update the facets_dict and return it. '''

        facets_dict = {
            'type': _('Portal Type'),
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
            'ready_to_publish': _('Record Status'),
            'imso_approval': _('IMSO Approval'),
            }

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
            'is_site_message_showing',
            'fgp_url',
            'contact_information',
            ])

    def before_map(self, map):
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
            'if_empty_generate_uuid': if_empty_generate_uuid,
            'canada_tags': canada_tags,
            'geojson_validator': geojson_validator,
            'protect_portal_release_date': protect_portal_release_date,
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
        search_params['fq'] = search_params['fq'].replace(
            'wbdisable:"true"', '').replace(
            'wbdisable:"false"', '')
        from pylons import c
        try:
            c.fields_grouped.pop('wbdisable', None)
        except:
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
        data_dict['spatial_representation_type'] = json.loads(data_dict.get(
            'spatial_representation_type', '[]'))

        if data_dict.get('portal_release_date'):
            data_dict.pop('ready_to_publish', None)
        elif data_dict.get('ready_to_publish') == 'true':
            data_dict['ready_to_publish'] = 'true'
        else:
            data_dict['ready_to_publish'] = 'false'

        return data_dict

    def before_view(self, pkg_dict):
        return pkg_dict

    def after_create(self, context, data_dict):
        return data_dict

    def after_update(self, context, data_dict):
        if context.get('allow_state_change') and data_dict.get(
                'state') == 'active':
            h.flash_success(
                _("Your asset %s has been saved.")
                % data_dict['id']
            )
        return data_dict

    def after_delete(self, context, data_dict):
        return data_dict

    def after_show(self, context, data_dict):
        return data_dict

    def update_facet_titles(self, facet_titles):
        return facet_titles
