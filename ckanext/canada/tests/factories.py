from ckan.tests.factories import Organization
from uuid import uuid4

class CanadaOrganization(Organization):
    shortform = {
        'en': 'Test Org Shortform',
        'fr': 'Test FR Org Shortform'
    }
    title_translated = {
        'en': 'Test Org Title',
        'fr': 'Test FR Org Title'
    }
    faa_schedule = 'NA'
    name = uuid4().hex