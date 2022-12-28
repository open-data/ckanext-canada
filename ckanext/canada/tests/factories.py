from ckan.tests.factories import Organization, Dataset, Resource


class CanadaOrganization(Organization):
    shortform = {
        'en': 'Test Org Shortform',
        'fr': 'Test FR Org Shortform'}
    title_translated = {
        'en': 'Test Org Title',
        'fr': 'Test FR Org Title'}
    faa_schedule = 'NA'


class CanadaResource(Resource):
    name_translated = {
        'en': 'Test Resource',
        'fr': 'Test FR Resource'}
    resource_type = 'dataset'
    format = 'CSV'
    language = 'en'


class CanadaDataset(Dataset):
    name = None
    collection = 'primary'
    title_translated = {
        'en': 'Test Dataset',
        'fr': 'Test FR Dataset'}
    notes_translated = {
        'en': 'Test Notes',
        'fr': 'Test FR Notes'}
    license_id = 'ca-ogl-lgo'
    subject = 'arts_music_literature'
    keywords = {
        'en': ['Test', 'Keywords'],
        'fr': ['Test', 'FR', 'Keywords']}
    date_published = '2000-01-01'
    ready_to_publish = 'false'
    frequency = 'as_needed'
    jurisdiction = 'federal'
    restrictions = 'unrestricted'
    imso_approval = 'true'

