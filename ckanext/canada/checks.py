import attrs
from frictionless import Check
from frictionless.errors import HeaderError

from ckan.plugins.toolkit import _
from ckanext.datastore.helpers import is_valid_field_name


class DatastoreInvalidHeader(HeaderError):
    type = "datastore-invalid-header"
    title = _("Invalid Header for DataStore")
    description = _("Column name is invalid for a DataStore header.\n\n How it could be resolved:\n - Remove any leading underscores('_') from the column name.\n - Remove any leading or trailing white space from the column name.\n - Remove any double quotes('\"') from the column name.\n - Make sure the column name is not blank.")
    template = _("Column name {value} in column {column_number} is not valid for a DataStore header")


class DatastoreTooLongHeader(HeaderError):
    type = "datastore-header-too-long"
    title = _("Header Too Long for DataStore")
    description = _("Column name is too long for a DataStore header.\n\n How it could be resolved:\n - Make the column name at most 63 characters long.")
    template = _("Column name {value} in column {column_number} is too long for a DataStore header")


@attrs.define(kw_only=True, repr=False)
class DatastoreHeadersCheck(Check):
    type = "ds-headers"
    Errors = [DatastoreInvalidHeader, DatastoreTooLongHeader]

    # Validate

    def validate_start(self):
        index = 0
        for header in self.resource.labels:
            if not is_valid_field_name(header):
                yield DatastoreInvalidHeader(
                    note=_("Column name {value} in column {column_number} is not valid for a DataStore header").format(value=header,
                                                                                                                       column_number=index),
                    labels=[header],
                    row_numbers=[index]
                )

            if len(header) > 63:
                yield DatastoreTooLongHeader(
                    note=_("Column name {value} in column {column_number} is too long for a DataStore header").format(value=header,
                                                                                                                      column_number=index),
                    labels=[header],
                    row_numbers=[index]
                )


            index += 1

    # Metadata

    metadata_profile_patch = {
        "type": "object",
        "properties": {},
    }
