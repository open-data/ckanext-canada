from ckan.logic.schema import (default_create_package_schema,
    default_update_package_schema, default_show_package_schema)
from ckan.logic.converters import (free_tags_only, convert_from_tags,
    convert_to_tags, convert_from_extras, convert_to_extras)
from ckan.lib.navl.validators import ignore_missing
from ckan.lib.navl.dictization_functions import Invalid, missing
from ckan.new_authz import is_sysadmin

from ckanext.canada.metadata_schema import schema_description

def create_package_schema():
    """
    Add our custom fields for validation from the form
    """
    schema = default_create_package_schema()
    _schema_update(schema, 'create')
    return schema

def update_package_schema():
    """
    Add our custom fields for validation from the form
    """
    schema = default_update_package_schema()
    _schema_update(schema, 'update')
    return schema

def show_package_schema():
    """
    Add our custom fields for converting from the db
    """
    schema = default_show_package_schema()
    _schema_update(schema, 'show')
    return schema

def _schema_update(schema, purpose):
    """
    :param schema: schema dict to update
    :param purpose: 'create', 'update' or 'show'
    """
    assert purpose in ('create', 'update', 'show')

    for name, lang, field in schema_description.dataset_field_iter():
        if name == 'name' and purpose == 'create':
            schema[name] = [ignore_missing, unicode]

        if name in schema:
            continue # don't modify existing fields.. yet

        v = _schema_field_validators(name, lang, field)
        if v is not None:
            schema[name] = v[0] if purpose != 'show' else v[1]

    for name in ('maintainer', 'author', 'author_email',
            'maintainer_email', 'license_id', 'department_number'):
        del schema[name]

    if purpose == 'show':
        schema['tags']['__extras'].append(free_tags_only)

def _schema_field_validators(name, lang, field):
    """
    return a tuple with lists of validators for the field:
    one for create/update and one for show, or None to leave
    both lists unchanged
    """
    if name in ('id', 'language'):
        return

    if name == 'portal_release_date':
        return ([treat_missing_as_empty, protect_date_published,
                 unicode, convert_to_extras],
                [convert_from_extras, ignore_missing])

    if 'vocabulary' in field:
        return ([convert_to_tags(field['vocabulary'])],
                [convert_from_tags(field['vocabulary'])])

    edit = []
    if field['type'] in ('calculated', 'fixed') or not field['mandatory']:
        edit.append(ignore_missing)

    return (edit + [unicode, convert_to_extras],
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


