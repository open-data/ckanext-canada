# -*- coding: UTF-8 -*-
from ckan.tests.factories import User, Organization, Dataset, Resource, ResourceView
from factory import LazyAttribute
import ckan.tests.helpers as helpers
from ckan.model import Session


class CanadaUser(User):
    @classmethod
    def _create(self, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        # The ckan.tests.factories.User does not add the user to a session
        # so we need to override the _create method to add the user to the
        # session to prevent DetachedInstanceError execptions from being raised
        user = target_class(**dict(kwargs, sysadmin=False))
        Session.add(user)
        Session.commit()
        Session.remove()

        # We want to return a user dict not a model object, so call user_show
        # to get one. We pass the user's name in the context because we want
        # the API key and other sensitive data to be returned in the user dict
        user_dict = helpers.call_action('user_show', id=user.id,
                                        context={'user': user.name})
        return user_dict


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
    portal_release_date = '2000-01-01'
    ready_to_publish = 'false'
    frequency = 'as_needed'
    jurisdiction = 'federal'
    restrictions = 'unrestricted'
    imso_approval = 'true'

