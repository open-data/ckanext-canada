from copy import copy
from goodtables import check, Error
from tabulator.exceptions import TabulatorException
import json

from ckan.plugins.toolkit import _, config
from ckanext.datastore.helpers import is_valid_field_name


@check('ds-headers', type='custom', context='head')
def ds_headers_check(cells, sample=None):
    # type: (list[dict], list[dict]|None) -> list[Error|None]
    """
    Checks header values against the DataStore constraints
    """
    errors = []
    for cell in copy(cells):

        # Skip if not header
        if 'header' not in cell:
            continue

        errored = False

        if not is_valid_field_name(cell['value']):
            errors.append(Error('datastore-invalid-header', cell,
                                message=_("Column name {value} in column {column_number} is not valid for a DataStore header"),
                                message_substitutions={'value': cell['value'],}))
            errored = True
        if len(cell['value']) > 63:
            errors.append(Error('datastore-header-too-long', cell,
                                message=_("Column name {value} in column {column_number} is too long for a DataStore header"),
                                message_substitutions={'value': cell['value'],}))
            errored = True

        if errored:
            cells.remove(cell)

    return errors


@check('static-dialect', type='custom')
class StaticDialectCheck(object):

    static_dialects = None
    static_dialect = None
    stream_dialect = None
    errors = None

    def __init__(self, **options):
        static_dialects = config.get(
            u'ckanext.canada.tabulator_dialects')
        if static_dialects:
            self.static_dialects = json.loads(static_dialects)

    def prepare(self, stream, schema, extra):
        if self.static_dialects:
            # need to retrieve static dialect here as we have the format.
            self.static_dialect = self.static_dialects.get(stream.format, None)
        try:
            self.stream_dialect = stream.dialect
        except TabulatorException as e:
            self.errors = e.message
            pass

        # always return True so we use this check
        return True

    def check_file(self):
        """
        Custom from canada fork of goodtables.

        Return errors list and bool of fatal error or not
        """
        if not self.static_dialect:
            return []

        errors = []

        if self.errors and isinstance(self.errors, list):
            for err_id, err_msg in self.errors:
                errors.append(Error(err_id, message=err_msg))

        return errors, len(errors) > 0
