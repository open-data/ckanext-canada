from pylons.i18n import _
import ckan.plugins as p
from ckan.lib.base import render
from ckan.lib.plugins import DefaultDatasetForm
from ckan.logic.action import create
from wcms import wcms_configure
from routes.mapper import SubMapper
from logging import getLogger
from ckanext.canada.metadata_schema import schema_description
from ckanext.canada.navl_schema import (if_empty_generate_uuid, canada_tags,
    geojson_validator)
from ckanext.canada import logic
from ckanext.canada import helpers

import json

# Ugly monkey patch to let us hook into the user_create action

ckan_user_create = create.user_create
ckan_user_create_dict = {}


def notify_ckan_user_create(context, data_dict):
    """
    Send an e-mail notification about new users that register on the site to the configured recipient
    @param context: standard context object
    @param data_dict: dictionary with field values from the user registration form.
    @raise:
    """

    ckan_user_create(context, data_dict)

    import ckan.lib.mailer

    try:
        if ckan_user_create_dict['email_address']:
            new_email = str(data_dict['email']).strip()
            new_fullname = str(data_dict['fullname']).strip()
            new_username = str(data_dict['name']).strip()
            new_phoneno = str(data_dict['phoneno']).strip()
            new_dept = str(data_dict['department']).strip()

            xtra_vars = {'email': new_email, 'fullname': new_fullname, 'username': new_username,
                         'phoneno': new_phoneno, 'dept': new_dept}
            email_body = render('user/new_user_email.html', extra_vars=xtra_vars)
            ckan.lib.mailer.mail_recipient(ckan_user_create_dict['email_name'], ckan_user_create_dict['email_address'],
                   u'New data.gc.ca Registry Account Created / Nouveau compte cr\u00e9\u00e9 dans le registre de Gouvernement ouvert',
                   email_body)
    except ckan.lib.mailer.MailerException as m:
        log = getLogger('ckanext')
        log.error(m.message)


class DataGCCAInternal(p.SingletonPlugin):
    """
    Plugin for internal version of data.gc.ca site, aka the "registry"
    This plugin requires the DataGCCAPublic and DataGCCAForms plugins
    """
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer)
    p.implements(p.IFacets)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IRoutes, inherit=True)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates/internal')

    def dataset_facets(self, facets_dict, package_type):
        ''' Update the facets_dict and return it. '''
        return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):
        ''' Update the facets_dict and return it. '''
        return facets_dict

    def organization_facets(self, facets_dict, organization_type, package_type):
        ''' Update the facets_dict and return it. '''
        return facets_dict

    def before_map(self, map):
        map.connect('/', controller='user', action='login')
        map.connect('/user/logged_in', action='logged_in',
            controller='ckanext.canada.controller:CanadaController')
        map.connect('/publish', action='search', 
            controller='ckanext.canada.controller:PublishController')
        map.connect('/publish_datasets', action='publish', conditions= dict(method=['POST']),
            controller='ckanext.canada.controller:PublishController')
        map.connect('/user/register', action='register',
                    controller='ckanext.canada.controller:CanadaController')
        return map

    def after_map(self, map):
        with SubMapper(map,
                controller='ckanext.canada.controller:CanadaController') as m:
            m.connect('/guidelines', action='view_guidelines')
            m.connect('/help', action='view_help')
            m.connect('/newuser', action='view_new_user')
        return map

    def get_helpers(self):
        return dict((h, getattr(helpers, h)) for h in [
            'may_publish_datasets',
            'today',
            'date_format',
            'parse_release_date_facet',
            'is_ready_to_publish',
            'get_datapreview_ati',
            'get_datapreview_contracts',
            ])

    def configure(self, config):
        if 'ckan.drupal.url' in config:
            wcms_configure(config['ckan.drupal.url'])

        if 'canada.notification_new_user_email' in config:
            ckan_user_create_dict['email_address'] = config['canada.notification_new_user_email']
            if 'canada.notification_new_user_name' in config:
                ckan_user_create_dict['email_name'] = config['canada.notification_new_user_name']
            else:
                ckan_user_create_dict['email_name'] = config['canada.notification_new_user_email']
            create.user_create = notify_ckan_user_create

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

    def dataset_facets(self, facets_dict, package_type):
        ''' Update the facets_dict and return it. '''

        facets_dict = {
                      'keywords': _('Tags'),
                      'keywords_fra': _('Tags'),
                      'res_format': _('File Format'),
                      'catalog_type': _('Collection Type'),
                      'subject': _('Subject'),
                      'organization': _('Organization'),
                      'ready_to_publish': _('Ready to Publish'),
                      'license_id': _('Licence') }

        return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):
        ''' Update the facets_dict and return it. '''
        return facets_dict

    def organization_facets(self, facets_dict, organization_type, package_type):
        ''' Update the facets_dict and return it. '''

        facets_dict = {
                      'keywords': _('Tags'),
                      'keywords_fra': _('Tags'),
                      'res_format': _('File Format'),
                      'catalog_type': _('Collection Type'),
                      'subject': _('Subject'),
                      'ready_to_publish': _('Ready to Publish'),
                      'license_id': _('Licence') }

        return facets_dict

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
        #we're going to group portal_release_date into two bins - to today and after today        
        search_params['facet.range'] = 'portal_release_date'
        search_params['facet.range.start'] = 'NOW/DAY-100YEARS'
        search_params['facet.range.end'] = 'NOW/DAY+100YEARS'
        search_params['facet.range.gap'] = '+100YEARS'
        
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
        data_dict['keywords_fra'] = kw.get('fr')
        data_dict['catalog_type'] = data_dict.get('type', '')
        
        data_dict['subject'] = json.loads(data_dict.get('subject', '[]'))

        if 'portal_release_date' in data_dict:
            data_dict.pop('ready_to_publish', None)
        elif 'extras_ready_to_publish' in data_dict and data_dict['extras_ready_to_publish'] == 'true':
            data_dict['ready_to_publish'] = 'true'
        else:
            data_dict['ready_to_publish'] = 'false'
        
        return data_dict

    def before_view(self, pkg_dict):
        return pkg_dict

    def after_create(self, context, data_dict):
        return data_dict

    def after_update(self, context, data_dict):
        return data_dict

    def after_delete(self, context, data_dict):
        return data_dict

    def after_show(self, context, data_dict):
        return data_dict

    def update_facet_titles(self, facet_titles):
        return facet_titles

