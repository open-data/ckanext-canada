from copy import copy
from goodtables import check, Error
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

    validation_options = None
    static_dialect = None
    stream_dialect = None

    def __init__(self, **options):
        static_validation_options = config.get(
            u'ckanext.validation.static_validation_options')
        if static_validation_options:
            self.validation_options = json.loads(static_validation_options)

    def prepare(self, stream, schema, extra):
        if self.validation_options:
            self.static_dialect = self.validation_options.get('dialect', {}) \
                .get(stream.format, None)
        self.stream_dialect = stream.dialect
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

        if 'delimiter' in self.stream_dialect and self.stream_dialect['delimiter'] != self.static_dialect['delimiter']:
            errors.append(Error('invalid-dialect',
                                message=_("File is using delimeter {stream_delimeter} instead of {static_delimeter}"),
                                message_substitutions={'stream_delimeter': self.stream_dialect['delimiter'],
                                                       'static_delimeter': self.static_dialect['delimiter'],}))

        if 'quoteChar' in self.stream_dialect and self.stream_dialect['quoteChar'] != self.static_dialect['quotechar']:
            errors.append(Error('invalid-quote-char',
                                message=_("File is using quoting character {stream_quote_char} instead of {static_quote_char}"),
                                message_substitutions={'stream_quote_char': self.stream_dialect['quoteChar'],
                                                       'static_quote_char': self.static_dialect['quotechar'],}))

        if 'doubleQuote' in self.stream_dialect and self.stream_dialect['doubleQuote'] != self.static_dialect['doublequote']:
            errors.append(Error('invalid-double-quote',
                                message=_("File is using double quoting {stream_double_quote} instead of {static_double_quote}"),
                                message_substitutions={'stream_double_quote': self.stream_dialect['doubleQuote'],
                                                       'static_double_quote': self.static_dialect['doublequote'],}))

        return errors, len(errors) > 0
