"""
Contains subclasses of Tabulator Stream and CSVParser and CSV Dialect.

Xloader and Validation plugins use these classes
to use static dialects with Tabulator.

The CSVParser is different from others, and needs some extra mangling.

Note: script cannot be named tabulator! (hence tabulate)
"""
from tabulator.stream import Stream
from tabulator.parsers.csv import CSVParser
from tabulator.config import CSV_SAMPLE_LINES
from tabulator.exceptions import TabulatorException, EncodingError
import six
import json
import csv
from csv import Dialect
from _csv import Dialect as _Dialect

from ckan.plugins.toolkit import config, _

from logging import getLogger, Filter


class LimitStreamLogging(Filter):
    logged_messages = []
    def filter(self, record):
        current_log = (record.module, record.levelno, record.msg)
        if current_log not in self.logged_messages:
            self.logged_messages.append(current_log)
            return True
        return False


log = getLogger(__name__)
log.addFilter(LimitStreamLogging())

# Xloader uses a universal decoder to pre-fligh guess
# the encoding of a file. We should allow some of the
# unicode type encoding sets/subsets.
ENCODING_SUBSETS = [
    'UTF-8-SIG',
    'UTF-8',
    'ascii',
    'ASCII',
]


class CanadaStream(Stream):
    """
    This is the stream for all file types (csv and tsv).

    TSVParser is fine, and will use the dialect property from here.

    CSVParer is different, and you need to pass:
        custom_parsers={'csv': CanadaCSVParser}
    into the Stream instantiation.
    """

    #FIXME: open calls __extract_sample which catches all exceptions
    #       and eats them, re-raising as stringified SourceError.
    #       implement and open and try/catch a custom exception.

    static_dialects = None
    static_encoding = None

    def __init__(self, source, *args, **kwargs):
        kwargs.update({'custom_parsers': {'csv': CanadaCSVParser}})
        encoding = _get_encoding()
        if encoding:
            self.static_encoding = encoding
        super(CanadaStream, self).__init__(source, *args, **kwargs)
        dialects = _get_dialects()
        if dialects:
            self.static_dialects = dialects

    @property
    def encoding(self):
        if self.static_encoding and super(CanadaStream, self).encoding != 'no':
            # if the stream does not have a guessed encoding yet, it will be set to 'no'.
            # we only want to compare encoding once the stream has guessed it.
            _check_encoding_and_raise(super(CanadaStream, self).encoding, self.static_encoding)
            return self.static_encoding

        return super(CanadaStream, self).encoding

    @property
    def dialect(self):
        """Dialect (if available)

        # Returns
            dict/None: dialect

        """
        if self.static_dialects and self.format in self.static_dialects:
            if self.static_encoding:
                log.debug('Using static encoding for %s: %s', self.format, self.static_encoding)
            log.debug('Using Static Dialect for %s: %r', self.format, self.static_dialects[self.format])
            _check_dialect_and_raise(super(CanadaStream, self).dialect, self.static_dialects[self.format])
            return self.static_dialects[self.format]

        return super(CanadaStream, self).dialect


class CanadaCSVDialect(Dialect):
    """
    Class containing a static CSV dialect, with support to pass in
    different dielect values.

    This class is only called from the mangling of CanadaCSVParser.__prepare_dialect,
    and thus will never be instantiated if ckanext.canada.tabulator_dialects is not set.
    """

    _name = 'csv'
    _valid = False
    # placeholders
    delimiter = ","
    quotechar = "\""
    escapechar = None
    doublequote = True
    skipinitialspace = False
    lineterminator = "\r\n"
    quoting = csv.QUOTE_MINIMAL

    def __init__(self, static_dialect):
        """
        Copied from csv.Dialect

        Adds passing in of static dialect.
        Needed to add py3/py2 compatibility for static dialect.
        """
        for k in static_dialect:
            if six.PY2 and isinstance(static_dialect[k], six.text_type):
                # must be strings and not unicode
                setattr(self, k, static_dialect[k].encode('utf-8'))
            else:
                setattr(self, k, static_dialect[k])
        if self.__class__ != Dialect and self.__class__ != CanadaCSVDialect:
            self._valid = True
        self._validate()

    def _validate(self):
        # will raise an exception if it is not a valid Dialect
        _Dialect(self)


class CanadaCSVParser(CSVParser):
    """
    CSVParser is different from the other Parsers as it uses
    __prepare_dialect instead of just the dialect property.

    We supply new options static_dialect and logger.

    We need to mangle __prepare_dialect if there is a static dialect.
    """

    static_dialects = None
    static_encoding = None

    # custom options, these need to exist for some magic.
    options = [
        'static_dialect',
        'static_encoding',
    ]

    def __init__(self, loader, *args, **kwargs):
        encoding = _get_encoding()
        if encoding:
            self.static_encoding = encoding
        super(CanadaCSVParser, self).__init__(loader, *args, **kwargs)
        dialects = _get_dialects()
        if dialects:
            # we only want to mangle the parent method if a static dialect
            # is being used. Otherwise, we want the parent method to be called as normal.
            self.static_dialects = dialects
            self._CSVParser__prepare_dialect = self.__mangle__prepare_dialect

    @property
    def encoding(self):
        if self.static_encoding and super(CanadaCSVParser, self).encoding != 'no':
            # if the stream does not have a guessed encoding yet, it will be set to 'no'.
            # we only want to compare encoding once the stream has guessed it.
            _check_encoding_and_raise(super(CanadaCSVParser, self).encoding, self.static_encoding)
            return self.static_encoding

        return super(CanadaCSVParser, self).encoding

    @property
    def dialect(self):
        if self.static_dialects and 'csv' in self.static_dialects:
            if self.static_encoding:
                log.debug('Using static encoding for csv: %s', self.static_encoding)
            log.debug('Using Static Dialect for csv: %r', self.static_dialects['csv'])
            _check_dialect_and_raise(super(CanadaCSVParser, self).dialect, self.static_dialects['csv'])
            return self.static_dialects['csv']

        return super(CanadaCSVParser, self).dialect

    def __mangle__prepare_dialect(self, stream):
        # Get sample
        # Copied from tabulator.pasrers.csv
        # Needed because we cannot call parent private method while mangling.
        sample = []
        while True:
            try:
                sample.append(next(stream))
            except StopIteration:
                break
            if len(sample) >= CSV_SAMPLE_LINES:
                break

        # Get dialect
        # Copied from tabulator.pasrers.csv
        # Needed to get the guessed dialect. Using mangling for protected properties.
        try:
            separator = b'' if six.PY2 else ''
            delimiter = self._CSVParser__options.get('delimiter', ',\t;|')
            dialect = csv.Sniffer().sniff(separator.join(sample), delimiter)
            if not dialect.escapechar:
                dialect.doublequote = True
        except csv.Error:
            class dialect(csv.excel):
                pass
        for key, value in self._CSVParser__options.items():
            setattr(dialect, key, value)
        # https://github.com/frictionlessdata/FrictionlessDarwinCore/issues/1
        if getattr(dialect, 'quotechar', None) == '':
            setattr(dialect, 'quoting', csv.QUOTE_NONE)

        self._CSVParser__dialect = dialect

        if self.static_encoding:
            log.debug('Using static encoding for csv: %s', self.static_encoding)
        log.debug('Using Static Dialect for csv: %r', self.static_dialects['csv'])

        # Xloader does not use Goodtables, and enters the Stream Parser fairly directly.
        # So we need to check and raise here. self.static_dialects will always exist in this mangle.
        _check_dialect_and_raise(self._CSVParser__dialect, CanadaCSVDialect(self.static_dialects['csv']), compare_obj=True)

        return sample, CanadaCSVDialect(self.static_dialects['csv'])


def _get_dialects():
    dialects = config.get('ckanext.canada.tabulator_dialects', None)
    if dialects:
        return json.loads(dialects)
    return None


def _get_encoding():
    return config.get('ckanext.canada.tabulator_encoding', None)


def _check_dialect_and_raise(guessed_dialect, static_dialect, compare_obj=False):
    errors = []

    guessed_delimiter_var = 'delimiter'
    guessed_quoteChar_var = 'quoteChar'
    guessed_doubleQuote_var = 'doubleQuote'

    if compare_obj:
        # a bit nasty, but need to compare from __mangle__prepare_dialect
        guessed_dialect = guessed_dialect.__dict__
        static_dialect = static_dialect.__dict__
        guessed_delimiter_var = 'delimiter'
        guessed_quoteChar_var = 'quotechar'
        guessed_doubleQuote_var = 'doublequote'

    if guessed_dialect and static_dialect:
        if guessed_delimiter_var in guessed_dialect and guessed_dialect[guessed_delimiter_var] != static_dialect['delimiter']:
            errors.append(('invalid-dialect', _("File is using delimeter {stream_delimeter} instead of {static_delimeter}").format(
                                                stream_delimeter=guessed_dialect[guessed_delimiter_var],
                                                static_delimeter=static_dialect['delimiter'])))

        if guessed_quoteChar_var in guessed_dialect and guessed_dialect[guessed_quoteChar_var] != static_dialect['quotechar']:
            errors.append(('invalid-quote-char', _("File is using quoting character {stream_quote_char} instead of {static_quote_char}").format(
                                                   stream_quote_char=guessed_dialect[guessed_quoteChar_var],
                                                   static_quote_char=static_dialect['quotechar'])))

        if guessed_doubleQuote_var in guessed_dialect and guessed_dialect[guessed_doubleQuote_var] != static_dialect['doublequote']:
            errors.append(('invalid-double-quote', _("File is using double quoting {stream_double_quote} instead of {static_double_quote}").format(
                                                     stream_double_quote=guessed_dialect[guessed_doubleQuote_var],
                                                     static_double_quote=static_dialect['doublequote'])))

    if errors:
        raise TabulatorException(errors)


def _check_encoding_and_raise(guessed_encoding, static_encoding):
    if guessed_encoding in ENCODING_SUBSETS or guessed_encoding == static_encoding:
        return
    raise EncodingError(_('File must be encoded with: %s' % static_encoding))
