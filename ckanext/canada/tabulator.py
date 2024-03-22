"""
Contains subclasses of Tabulator Stream and CSVParser and CSV Dialect.

Xloader and Validation plugins use these classes
to use static dialects with Tabulator.

The CSVParser is different from others, and needs some extra mangling.
"""
from tabulator import Stream
from tabulator.parsers.csv import CSVParser
from tabulator.config import CSV_SAMPLE_LINES
import six
from csv import Dialect
from _csv import Dialect as _Dialect


class CanadaStream(Stream):
    """
    This is the stream for all file types (csv and tsv).

    TSVParser is fine, and will use the dialect property from here.

    CSVParer is different, and you need to pass:
        custom_parsers={'csv': CanadaCSVParser}
    into the Stream instantiation.
    """

    def __init__(self, source, *args, **kwargs):
        super(CanadaStream, self).__init__(source, *args, **kwargs)
        self.static_dialect = kwargs.get('static_dialect', None)
        self.logger = kwargs.get('logger', None)

    @property
    def dialect(self):
        """Dialect (if available)

        # Returns
            dict/None: dialect

        """
        if self.static_dialect:
            if self.logger:
                self.logger.info('Using Static Dialect for %s: %r', self.__format, self.static_dialect)
            return self.static_dialect
        return super(CanadaStream, self).dialect


class CanadaCSVDialect(Dialect):

    _name = 'csv'
    _valid = False
    # placeholders
    delimiter = None
    quotechar = None
    escapechar = None
    doublequote = None
    skipinitialspace = None
    lineterminator = None
    quoting = None

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

    # custom options, these need to exist for some magic.
    options = [
        'static_dialect',
        'logger',
    ]

    def __init__(self, loader, *args, **kwargs):
        super(CanadaCSVParser, self).__init__(loader, *args, **kwargs)
        self.static_dialect = kwargs.get('static_dialect', None)
        self.logger = kwargs.get('logger', None)
        # we only want to mangle the parent method if a static dialect
        # is supplied. Otherwise, we want the parent method to be called as normal.
        if self.static_dialect:
            self._CSVParser__prepare_dialect = self.__mangle__prepare_dialect

    @property
    def dialect(self):
        if self.static_dialect:
            if self.logger:
                self.logger.info('Using Static Dialect for csv: %r', self.static_dialect)
            return self.static_dialect
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

        if self.logger:
            self.logger.info('Using Static Dialect for csv: %r', self.static_dialect)

        return sample, CanadaCSVDialect(self.static_dialect)
