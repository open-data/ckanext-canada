# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN

from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaUser as User,
)

from ckanext.recombinant.tables import get_chromo


class TestCanadaTriggers(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestCanadaTriggers, self).setup_method(method)

        self.editor = User()
        self.editor2 = User()
        self.org = Organization(umd_number='example_umd',
                                department_number='example_department',
                                users=[{'name': self.editor['name'],
                                        'capacity': 'editor'},
                                       {'name': self.editor2['name'],
                                        'capacity': 'editor'}])
        self.editor_action = LocalCKAN(username=self.editor['name']).action
        self.editor2_action = LocalCKAN(username=self.editor2['name']).action
        self.sys_action = LocalCKAN().action


    def _setup_pd(self, type, nil_type=None):
        assert type

        self.sys_action.recombinant_create(dataset_type=type, owner_org=self.org['name'])

        rval = self.editor_action.recombinant_show(dataset_type=type, owner_org=self.org['name'])

        chromo = get_chromo(type)

        self.editor_action.datastore_upsert(
            resource_id=rval['resources'][0]['id'],
            records=[chromo['examples']['record']])

        if nil_type:
            nil_chromo = get_chromo(nil_type)

            self.editor_action.datastore_upsert(
                resource_id=rval['resources'][1]['id'],
                records=[nil_chromo['examples']['record']])

        return rval['resources'][0]['id'], rval['resources'][1]['id'] if nil_type else None


    def test_update_record_modified_created_trigger(self):
        resource_id, nil_resource_id = self._setup_pd(type='ati', nil_type='ati-nil')

        #NOTE: we use datastore_search_sql to get nanosecond timestamps

        chromo = get_chromo('ati')

        result = self.sys_action.datastore_search_sql(
            sql="SELECT %s from \"%s\"" % (', '.join(f['datastore_id'] for f in chromo['fields']), resource_id))
        record_data_dict = result['records'][0]

        assert record_data_dict['user_modified'] == self.editor['name']
        assert record_data_dict['record_created'] == record_data_dict['record_modified']

        record_data_dict['summary_en'] = 'New English Summary'
        record_data_dict['summary_fr'] = 'New French Summary'

        initial_created_time = record_data_dict['record_created']
        initial_modified_time = record_data_dict['record_modified']
        initial_user_modified = record_data_dict['user_modified']

        # upsert data as system user
        self.sys_action.datastore_upsert(
            resource_id=resource_id,
            records=[record_data_dict])

        # return of datastore_upsert does not have triggered values, go get
        result = self.sys_action.datastore_search_sql(
            sql="SELECT record_created, record_modified, user_modified from \"%s\"" % resource_id)

        record = result['records'][0]

        # sysadmin upserts should not modify these values
        assert record['record_created'] == initial_created_time
        assert record['user_modified'] == initial_user_modified
        assert record['record_modified'] == initial_modified_time

        record_data_dict['summary_en'] = 'Even Newer English Summary'
        record_data_dict['summary_fr'] = 'Even Newer French Summary'

        # upsert data as a different editor user
        self.editor2_action.datastore_upsert(
            resource_id=resource_id,
            records=[record_data_dict])

        # return of datastore_upsert does not have triggered values, go get
        result = self.sys_action.datastore_search_sql(
            sql="SELECT record_created, record_modified, user_modified from \"%s\"" % resource_id)

        record = result['records'][0]

        # non-sysadmin upserts should modify user_modified and record_modified
        assert record['record_created'] == initial_created_time
        assert record['user_modified'] != initial_user_modified
        assert record['record_modified'] != initial_modified_time
