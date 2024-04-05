from copy import copy
from goodtables import check, Error

from ckan.plugins.toolkit import _
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
