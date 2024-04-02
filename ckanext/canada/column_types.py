from ckanext.tabledesigner.column_types import ChoiceColumn, TextColumn
from ckanext.datastore.backend.postgres import literal_string, identifier

def _(x):
    return x

class Province(ChoiceColumn):
    label = _("Canadian Province or Territory")
    description = _(
        "based on data reference standard "
        "https://open.canada.ca/data/en/dataset/"
        "cd8fad92-b276-4250-972f-2d6c40ca04fa/"
    )
    example = 'AB'
    design_snippet = None  # disable from parent ChoiceColumn
    view_snippet = 'province.html'

    def choices(self):
        return {
            'AB': _('Alberta'),
            'BC': _('British Columbia'),
            'MB': _('Manitoba'),
            'NB': _('New Brunswick'),
            'NL': _('Newfoundland and Labrador'),
            'NT': _('Northwest Territories'),
            'NS': _('Nova Scotia'),
            'NU': _('Nunavut'),
            'ON': _('Ontario'),
            'PE': _('Prince Edward Island'),
            'QC': _('Quebec'),
            'SK': _('Saskatchewan'),
            'YT': _('Yukon'),
        }

    @classmethod
    def datastore_field_schema(cls, td_ignore, td_pd):
        # Remove tdchoices from parent ChoiceColumn
        return {}


class CRABusinessNumber(TextColumn):
    label = _('CRA Business Number')
    description = _('9-digit CRA business number (upcoming data standard)')
    example = '987654321'
    view_snippet = 'cra_business_number.html'

    # remove surrounding whitespace and validate
    _SQL_VALIDATE = '''
    {value} := trim({value});
    IF {value} <> '' AND regexp_match({value}, {pattern}) IS NULL THEN
        errors := errors || ARRAY[{colname}, {error}];
    END IF;
    '''

    _BUSINESS_NUMBER_PATTERN = r'\d{9}'

    def sql_validate_rule(self):
        return self._SQL_VALIDATE.format(
            value='NEW.' + identifier(self.colname),
            pattern=literal_string(self._BUSINESS_NUMBER_PATTERN),
            colname=literal_string(self.colname),
            error=literal_string(_('Invalid business number')),
        )

    def excel_validate_rule(self):
        # COUNT(FIND(...)) lets us accept single-quote-prefixed values
        # like "'012345678" as a business number
        return (
            'OR(COUNT(FIND({{0,1,2,3,4,5,6,7,8,9}},{_value_}))<>9,'
            'LEN({_value_})<>9)'
        )
