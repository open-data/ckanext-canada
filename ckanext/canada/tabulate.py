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
import six
import json
from csv import Dialect
from _csv import Dialect as _Dialect
from csv import QUOTE_MINIMAL

from ckan.plugins.toolkit import config

from logging import getLogger, Filter

log2 = getLogger('ckanext.canada.dev')

class LimitStreamLogging(Filter):
    logged_messages = []
    #TODO: solve duplicative log messages
    def filter(self, record):
        # add other fields if you need more granular comparison, depends on your app
        current_log = (record.module, record.levelno, record.msg)
        if current_log not in self.logged_messages:
            self.logged_messages.append(current_log)
            return True
        return False


log = getLogger(__name__)
log.addFilter(LimitStreamLogging())


class CanadaStream(Stream):
    """
    This is the stream for all file types (csv and tsv).

    TSVParser is fine, and will use the dialect property from here.

    CSVParer is different, and you need to pass:
        custom_parsers={'csv': CanadaCSVParser}
    into the Stream instantiation.
    """

    static_dialects = None
    encoding = None

    def __init__(self, source, *args, **kwargs):
        kwargs.update({'custom_parsers': {'csv': CanadaCSVParser}})
        super(CanadaStream, self).__init__(source, *args, **kwargs)
        dialects = _get_dialects()
        if dialects:
            self.static_dialects = dialects
        encoding = _get_encoding()
        if encoding:
            self.encoding = encoding

    @property
    def dialect(self):
        """Dialect (if available)

        # Returns
            dict/None: dialect

        """
        if self.static_dialects and self.format in self.static_dialects:
            if self.encoding:
                log.info('Using static encoding for %s: %s', self.format, self.encoding)
            log.info('Using Static Dialect for %s: %r', self.format, self.static_dialects[self.format])
            # remove logger propagation to prevent excess logging
            log.propagate = False

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
    quoting = QUOTE_MINIMAL

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
    encoding = None

    # custom options, these need to exist for some magic.
    options = [
        'static_dialect',
        'encoding',
    ]

    def __init__(self, loader, *args, **kwargs):
        super(CanadaCSVParser, self).__init__(loader, *args, **kwargs)
        dialects = _get_dialects()
        if dialects:
            # we only want to mangle the parent method if a static dialect
            # is being used. Otherwise, we want the parent method to be called as normal.
            self.static_dialects = dialects
            self._CSVParser__prepare_dialect = self.__mangle__prepare_dialect
        encoding = _get_encoding()
        if encoding:
            self.encoding = encoding

    @property
    def dialect(self):
        if self.static_dialects and 'csv' in self.static_dialects:
            if self.encoding:
                log.info('Using static encoding for csv: %s', self.encoding)
            log.info('Using Static Dialect for csv: %r', self.static_dialects['csv'])
            # remove logger propagation to prevent excess logging
            log.propagate = False

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

        if self.encoding:
            log.info('Using static encoding for csv: %s', self.encoding)
        log.info('Using Static Dialect for csv: %r', self.static_dialects['csv'])
        # remove logger propagation to prevent excess logging
        log.propagate = False

        return sample, CanadaCSVDialect(self.static_dialects['csv'])


def _get_dialects():
    dialects = config.get('ckanext.canada.tabulator_dialects', None)
    if dialects:
        return json.loads(dialects)
    return None


def _get_encoding():
    return config.get('ckanext.canada.tabulator_encoding', None)
