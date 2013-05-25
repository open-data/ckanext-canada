from pylons.i18n import _
import ckan.plugins as p
from ckan.lib.plugins import DefaultDatasetForm
import ckan.lib.plugins as lib_plugins
from ckan.plugins import toolkit
from routes.mapper import SubMapper

from ckanext.canada.metadata_schema import schema_description
from ckanext.canada.navl_schema import (create_package_schema,
    update_package_schema, show_package_schema)
from ckanext.canada.logic import (group_show, organization_show,
    changed_packages_activity_list_since)
from ckanext.canada import helpers


class DataGCCAInternal(p.SingletonPlugin):
    """
    Plugin for internal version of data.gc.ca site, aka the "registry"
    This plugin requires the DataGCCAPublic and DataGCCAForms plugins
    """
    p.implements(p.IConfigurer)
    p.implements(p.IFacets)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IRoutes, inherit=True)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates/internal')

    def dataset_facets(self, facets_dict, package_type):
        ''' Update the facets_dict and return it. '''

        facets_dict.update({'published': _('Published or Pending')})

        return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):
        ''' Update the facets_dict and return it. '''
        return facets_dict

    def organization_facets(self, facets_dict, organization_type, package_type):
        ''' Update the facets_dict and return it. '''

        facets_dict = {
                      'tags': _('Subject'),
                      'res_format': _('File Format'),
                      'raw_geo': _('Catalog Type'), }

        return facets_dict

    def before_map(self, map):
        map.connect('/', controller='user', action='login')
        map.connect(
            'organizations_index', '/organization',
            controller='ckanext.canada.controller:CanadaController',
            action='organization_index',
        )
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
            ])


class DataGCCAPublic(p.SingletonPlugin):
    """
    Plugin for public-facing version of data.gc.ca site, aka the "portal"
    This plugin requires the DataGCCAForms plugin
    """
    p.implements(p.IConfigurer)
    p.implements(p.IFacets)
    p.implements(p.ITemplateHelpers)

    def update_config(self, config):
        # add our templates
        p.toolkit.add_template_directory(config, 'templates/public')
        p.toolkit.add_public_directory(config, 'public')

    def dataset_facets(self, facets_dict, package_type):
        ''' Update the facets_dict and return it. '''

        facets_dict.update( {
                      'tags': _('Subject'),
                      'res_format': _('File Format'),
                      'raw_geo': _('Catalog Type'),
                      'organization': _('Organization'), } )

        return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):
        ''' Update the facets_dict and return it. '''
        return facets_dict

    def organization_facets(self, facets_dict, organization_type, package_type):
        ''' Update the facets_dict and return it. '''
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
            ])


class DataGCCAForms(p.SingletonPlugin, DefaultDatasetForm):
    """
    Plugin for dataset forms for Canada's metadata schema
    """
    p.implements(p.IConfigurable)
    p.implements(p.IActions)
    p.implements(p.IDatasetForm, inherit=True)

    # IConfigurable

    def configure(self, config):
        jinja_globals = config['pylons.app_globals'].jinja_env.globals
        jinja_globals['schema_description'] = schema_description

    # IActions

    def get_actions(self):
        return {
            'group_show': group_show,
            'organization_show': organization_show,
            'changed_packages_activity_list_since':
                changed_packages_activity_list_since,
            }

    # IDatasetForm

    def is_fallback(self):
        """
        Return True to register this plugin as the default handler for
        package types not handled by any other IDatasetForm plugin.
        """
        return True

    def package_types(self):
        """
        This plugin doesn't handle any special package types, it just
        registers itself as the default (above).
        """
        return []

    def create_package_schema(self):
        return create_package_schema()

    def update_package_schema(self):
        return update_package_schema()

    def show_package_schema(self):
        return show_package_schema()


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
        return search_params

    def after_search(self, search_results, search_params):
        if search_results['count'] > 0:
            for result in search_results['results']:
        
                title_fra = filter(lambda extra:extra['key']=='title_fra', result['extras'])
                if len(title_fra) > 0:
                    result['title_fra'] = title_fra[0]['value']
                                 
                notes_fra = filter(lambda extra:extra['key']=='notes_fra', result['extras'])
                if len(notes_fra) > 0:
                    result['notes_fra'] =  notes_fra[0]['value']
        
        return search_results

    def before_index(self, data_dict):
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

