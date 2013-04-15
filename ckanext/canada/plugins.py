from pylons import c
import ckan.plugins as p
from ckan.lib.plugins import DefaultDatasetForm
import ckan.lib.plugins as lib_plugins
from ckan.logic.schema import (default_create_package_schema,
    default_update_package_schema, default_show_package_schema)
from ckan.logic.converters import (free_tags_only, convert_from_tags,
    convert_to_tags, convert_from_extras, convert_to_extras)
from ckan.lib.navl.validators import ignore_missing
from ckan.lib.navl.dictization_functions import Invalid, missing
from ckan.new_authz import is_sysadmin
from ckan.plugins import toolkit

from ckanext.canada.metadata_schema import schema_description
from ckanext.canada.logic import (group_show, organization_show,
    changed_packages_activity_list_since)


ORG_MAY_PUBLISH_KEY = 'publish'
ORG_MAY_PUBLISH_VALUE = 'True'

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

def create_package_schema():
    """
    Add our custom fields for validation from the form
    """
    schema = default_create_package_schema()
    _schema_update(schema, form_to_db=True)
    return schema

def update_package_schema():
    """
    Add our custom fields for validation from the form
    """
    schema = default_update_package_schema()
    _schema_update(schema, form_to_db=True)
    return schema

def show_package_schema():
    """
    Add our custom fields for converting from the db
    """
    schema = default_show_package_schema()
    _schema_update(schema, form_to_db=False)
    return schema

def _schema_update(schema, form_to_db):
    """
    schema: schema dict to update
    form_to_db: True for form_to_db_schema, False for db_to_form_schema
    """
    for name, lang, field in schema_description.dataset_field_iter():
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
        return ([treat_missing_as_empty, protect_date_published,
                 unicode, convert_to_extras],
                [convert_from_extras, ignore_missing])

    if 'vocabulary' in field:
        return ([convert_to_tags(field['vocabulary'])],
                [convert_from_tags(field['vocabulary'])])

    return ([ignore_missing, unicode, convert_to_extras],
            [convert_from_extras, ignore_missing])


def treat_missing_as_empty(key, data, errors, context):
    value = data.get(key, '')
    if value is missing:
        data[key] = ''

def protect_date_published(key, data, errors, context):
    """
    Ensure the date_published is not changed by an unauthorized user.
    """
    if is_sysadmin(context['user']):
        return
    original = ''
    package = context.get('package')
    if package:
        original = package.extras.get('date_published', '')
    value = data.get(key, '')
    if original == value:
        return

    for g in c.userobj.get_groups():
        if not g.is_organization:
            continue
        if g.extras.get(ORG_MAY_PUBLISH_KEY) == ORG_MAY_PUBLISH_VALUE:
            return

    raise Invalid('Cannot change value of key from %s to %s. '
                  'This key is read-only' % (original, value))


def ignore_missing_only_sysadmin(key, data, errors, context):
    """
    Ignore missing field *only* if the user is a sysadmin.
    """
    if is_sysadmin(context['user']):
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

