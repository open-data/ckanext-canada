# -*- coding: UTF-8 -*-
from ckan.tests.factories import Organization, Dataset, Resource, ResourceView
from factory import LazyAttribute


class CanadaOrganization(Organization):
    shortform = {
        'en': 'Test Org Shortform',
        'fr': 'Test FR Org Shortform'}
    title_translated = {
        'en': 'Test Org Title',
        'fr': 'Test FR Org Title'}
    faa_schedule = 'NA'


class CanadaResourceView(ResourceView):
    resource_id = LazyAttribute(lambda _: CanadaResource()['id'])
    title_fr = 'Test FR Resource View'


class CanadaResource(Resource):
    package_id = LazyAttribute(lambda _: CanadaDataset()['id'])
    name_translated = {
        'en': 'Test Resource',
        'fr': 'Test FR Resource'}
    resource_type = 'dataset'
    format = 'CSV'
    language = 'en'


class CanadaDataset(Dataset):
    owner_org = LazyAttribute(lambda _: CanadaOrganization()['id'])
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

