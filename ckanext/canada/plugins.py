from pylons import c
import ckan.plugins as p
from ckan.lib.plugins import DefaultDatasetForm
import ckan.lib.plugins as lib_plugins
from ckan.logic.converters import (free_tags_only, convert_from_tags,
    convert_to_tags, convert_from_extras, convert_to_extras)
from ckan.lib.navl.validators import ignore_missing
from ckan.lib.navl.dictization_functions import Invalid
from ckan.plugins import toolkit

from ckanext.canada.metadata_schema import schema_description

class DataGCCAPublic(p.SingletonPlugin):
    """
    Plugin for public-facing version of data.gc.ca site, aka the "portal"
    This plugin requires the DataGCCAForms plugin
    """
    p.implements(p.IConfigurer)

    def update_config(self, config):
        # add our templates
        p.toolkit.add_template_directory(config, 'templates/public')
        p.toolkit.add_public_directory(config, 'public')


class DataGCCAInternal(p.SingletonPlugin):
    """
    Plugin for internal version of data.gc.ca site, aka the "registry"
    This plugin requires the DataGCCAPublic and DataGCCAForms plugins
    """
    p.implements(p.IConfigurer)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates/internal')


class DataGCCAForms(p.SingletonPlugin, DefaultDatasetForm):
    """
    Plugin for dataset forms for Canada's metadata schema
    """
    p.implements(p.IConfigurable)
    p.implements(p.IDatasetForm, inherit=True)

    def configure(self, config):
        jinja_globals = config['pylons.app_globals'].jinja_env.globals
        jinja_globals['schema_description'] = schema_description

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
    
    def form_to_db_schema(self):
        """
        Add our custom fields for validation from the form
        """
        schema = super(DataGCCAForms, self).form_to_db_schema()
        _schema_update(schema, form_to_db=True)
        return schema

    def form_to_db_schema_api_create(self):
        """
        Add our custom fields for validation/conversion from the api
        """
        schema = super(DataGCCAForms, self).form_to_db_schema_api_create()
        _schema_update(schema, form_to_db=True)
        return schema

    def form_to_db_schema_api_update(self):
        """
        Add our custom fields for validation/conversion from the api
        """
        schema = super(DataGCCAForms, self).form_to_db_schema_api_update()
        _schema_update(schema, form_to_db=True)
        return schema

    def db_to_form_schema(self):
        """
        Add our custom fields for converting from the db
        """
        schema = super(DataGCCAForms, self).db_to_form_schema()
        _schema_update(schema, form_to_db=False)
        return schema
    
    def check_data_dict(self, data_dict, schema=None):
        # XXX: do nothing here because DefaultDatasetForm's check_data_dict()
        # breaks with the new three-stage dataset creation when using
        # convert_to_extras.
        pass


def _schema_update(schema, form_to_db):
    """
    schema: schema dict to update
    form_to_db: True for form_to_db_schema, False for db_to_form_schema
    """
    for name, lang, field in schema_description.dataset_fields_by_ckan_id():
        if name in schema:
            continue # don't modify existing fields.. yet

        v = _schema_field_validators(name, lang, field)
        if v is not None:
            schema[name] = v[0] if form_to_db else v[1]

    for name in ('maintainer', 'author', 'author_email',
            'maintainer_email', 'license_id', 'department_number'):
        del schema[name]

    if not form_to_db:
        schema['tags']['__extras'].append(free_tags_only)

def _schema_field_validators(name, lang, field):
    """
    return a tuple with lists of validators for the field:
    one for form_to_db and one for db_to_form, or None to leave 
    both lists unchanged
    """
    if name in ('id', 'language'):
        return

    if name == 'date_published':
        return ([protect_date_published, convert_to_extras],
            [convert_from_extras])

    if 'vocabulary' in field:
        return (
            [convert_to_tags(field['vocabulary'])],
            [convert_from_tags(field['vocabulary'])])

    return (
        [ignore_missing, unicode, convert_to_extras],
        [convert_from_extras, ignore_missing])


def protect_date_published(key, data, errors, context):
    """
    Ensure the date_published is not changed by an unauthorized user.
    """
    original = ''
    value = data.get(key, '')
    package = context.get('package')
    if package:
        original = package.extras['date_published']
    if original != value:
        raise Invalid('Cannot change value of key from %s to %s. '
                      'This key is read-only' % (original, value))


def ignore_missing_only_sysadmin(key, data, errors, context):
    """
    Ignore missing field *only* if the user is a sysadmin.
    """
    if c.is_sysadmin(context['user']):
        return ignore_missing(key, data, errors, context)


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

