# -*- coding: UTF-8 -*-
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckan.tests.helpers import reset_db
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo

import logging
log = logging.getLogger(__name__)


class TestBriefingT(object):
    @classmethod
    def setup_class(self):
        """Method is called at class level before all test methods of the class are called.
        Setup any state specific to the execution of the given class (which usually contains tests).
        """
        reset_db()

        log.info('Running setup for {}'.format(self.__class__.__name__))

        org = Organization()
        lc = LocalCKAN()

        log.info('Creating organization with id: {}'.format(org['name']))
        log.info('Setting organization dataset type to {}'.format('briefingt'))

        lc.action.recombinant_create(dataset_type='briefingt', owner_org=org['name'])
        rval = lc.action.recombinant_show(dataset_type='briefingt', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']


    def test_example(self):
        lc = LocalCKAN()
        record = get_chromo('briefingt')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])


    def test_blank(self):
        lc = LocalCKAN()
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{}])
        err = ve.value.error_dict
        expected = {}
        #TODO: assert the expected error
        assert ve is not None
