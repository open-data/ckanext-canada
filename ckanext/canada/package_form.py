from sqlalchemy.util import OrderedDict
from pylons.i18n import _
from ckan.forms import common, package

from ckanext.canada.metadata_schema import schema_description

def build_canada_package_form(is_admin=False, user_editable_groups=None,
        **kwargs):
    """
    Custom dataset editing form built from our metadata schema.
    """
    builder = package.build_package_form(
        user_editable_groups=user_editable_groups)

    for name, lang, f in schema_description.dataset_fields_by_ckan_id(False):
        factory = common.TextExtraField
        builder.add_field(factory(name))

    field_groups = []
    for section in schema_description.dataset_sections:
        fields = schema_description.dataset_fields_by_ckan_id(section=section)
        field_names = [name.encode('ascii') for name, lang, f in fields]
        field_groups.append((section['name']['en'].encode('ascii'),
            field_names))
    builder.set_displayed_fields(OrderedDict(field_groups))

    return builder

def get_canada_fieldset(is_admin=False, user_editable_groups=None, **kwargs):
    return build_canada_package_form(is_admin, user_editable_groups,
        **kwargs).get_fieldset()
