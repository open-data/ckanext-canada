# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN
from decimal import Decimal

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
        """
        The update_record_modified_created_trigger has a lot of scenarios
        regarding creating and updating records in teh DataStore tables.

        This test case tries to check all of those scenarios:
         - update as sysadmin does not change record_modified when provided
         - update as sysadmin does not change user_modified when provided
         - update as sysadmin changes record_created when provided
         - update as sysadmin does not change record_modified when not provided
         - update as non-sysadmin changes record_modified always
         - update as non-sysadmin changes user_modified always
         - update as non-sysadmin does not change record_created always
         - update as non-sysadmin changes record_modified when not provided
        """
        resource_id, nil_resource_id = self._setup_pd(type='ati', nil_type='ati-nil')

        # NOTE: we use datastore_search_sql to get nanosecond timestamps

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
        assert record['user_modified'] != initial_user_modified
        assert record['record_modified'] != initial_modified_time

        # try to update record_created
        record_data_dict['record_created'] = '2022-04-22T12:56:46.916648'

        # upsert data as a different editor user
        self.editor2_action.datastore_upsert(
            resource_id=resource_id,
            records=[record_data_dict])

        # return of datastore_upsert does not have triggered values, go get
        result = self.sys_action.datastore_search_sql(
            sql="SELECT record_created, record_modified, user_modified from \"%s\"" % resource_id)

        record = result['records'][0]

        # non-sysadmin upserts should not modify record_created
        assert record['record_created'] == initial_created_time

        # upsert data as system user
        self.sys_action.datastore_upsert(
            resource_id=resource_id,
            records=[record_data_dict])

        # return of datastore_upsert does not have triggered values, go get
        result = self.sys_action.datastore_search_sql(
            sql="SELECT record_created, record_modified, user_modified from \"%s\"" % resource_id)

        record = result['records'][0]

        # sysadmin upserts should modify record_created (for record restorations?)
        assert record['record_created'] != initial_created_time

        # remove record_modified to get a new value from the trigger
        record_data_dict.pop('record_modified', None)
        # need a new value somewhere so trigger knows columns are being updated
        record_data_dict['summary_en'] = 'Even Even Newerer English Summary'
        record_data_dict['summary_fr'] = 'Even Even Newerer French Summary'

        # upsert data as a different editor user
        self.editor2_action.datastore_upsert(
            resource_id=resource_id,
            records=[record_data_dict])

        # return of datastore_upsert does not have triggered values, go get
        result = self.sys_action.datastore_search_sql(
            sql="SELECT record_created, record_modified, user_modified from \"%s\"" % resource_id)

        record = result['records'][0]

        new_modified_time = record['record_modified']

        # non-sysadmin upserts should get a new record_modified, when it is not supplied
        assert record['record_modified'] != initial_modified_time

        # need a new value somewhere so trigger knows columns are being updated
        record_data_dict['summary_en'] = 'Even Even Even Newererer English Summary'
        record_data_dict['summary_fr'] = 'Even Even Even Newererer French Summary'

        # upsert data as a different editor user
        self.sys_action.datastore_upsert(
            resource_id=resource_id,
            records=[record_data_dict])

        # return of datastore_upsert does not have triggered values, go get
        result = self.sys_action.datastore_search_sql(
            sql="SELECT record_created, record_modified, user_modified from \"%s\"" % resource_id)

        record = result['records'][0]

        # sysadmin upserts should  NOT get a new record_modified, when it is not supplied
        assert record['record_modified'] != initial_modified_time
        assert record['record_modified'] == new_modified_time

    def test_money_type_rounding(self):
        """
        Money datastore fields should be rounded to 2 decimal places.

        Nullish values should be nullified.
        """

        # contractsa has a lot of money fields, so use it as a sample
        resource_id, nil_resource_id = self._setup_pd(type='contractsa')

        chromo = get_chromo('contractsa')

        result = self.sys_action.datastore_search_sql(
            sql="SELECT %s from \"%s\"" % (', '.join(f['datastore_id'] for f in chromo['fields']), resource_id))
        record_data_dict = result['records'][0]

        assert record_data_dict['contracts_goods_original_value'] == Decimal('50000.00')
        assert record_data_dict['contracts_goods_amendment_value'] == Decimal('500.00')
        assert record_data_dict['contracts_service_original_value'] == Decimal('50000.00')
        assert record_data_dict['contracts_service_amendment_value'] == Decimal('500.00')
        assert record_data_dict['contracts_construction_original_value'] == Decimal('50000.00')
        assert record_data_dict['contracts_construction_amendment_value'] == Decimal('500.00')
        assert record_data_dict['acquisition_card_transactions_total_value'] == Decimal('50000.00')

        record_data_dict['contracts_goods_original_value'] = '50000.7892983932'
        record_data_dict['contracts_goods_amendment_value'] = '500.0'
        record_data_dict['contracts_service_original_value'] = '50000'
        record_data_dict['contracts_service_amendment_value'] = '500.001111'
        record_data_dict['contracts_construction_original_value'] = '50000.0000000'
        record_data_dict['contracts_construction_amendment_value'] = '500.00999999'
        record_data_dict['acquisition_card_transactions_total_value'] = '50000.'

        self.sys_action.datastore_upsert(
            resource_id=resource_id,
            records=[record_data_dict])

        result = self.sys_action.datastore_search_sql(
            sql="SELECT %s from \"%s\"" % (', '.join(f['datastore_id'] for f in chromo['fields']), resource_id))
        record_data_dict = result['records'][0]

        assert record_data_dict['contracts_goods_original_value'] == Decimal('50000.79')
        assert record_data_dict['contracts_goods_amendment_value'] == Decimal('500.00')
        assert record_data_dict['contracts_service_original_value'] == Decimal('50000.00')
        assert record_data_dict['contracts_service_amendment_value'] == Decimal('500.00')
        assert record_data_dict['contracts_construction_original_value'] == Decimal('50000.00')
        assert record_data_dict['contracts_construction_amendment_value'] == Decimal('500.01')
        assert record_data_dict['acquisition_card_transactions_total_value'] == Decimal('50000.00')

        # contracts has conditional money fields, so test these for nullish values
        resource_id, nil_resource_id = self._setup_pd(type='contracts', nil_type='contracts-nil')

        chromo = get_chromo('contracts')

        result = self.sys_action.datastore_search_sql(
            sql="SELECT %s from \"%s\"" % (', '.join(f['datastore_id'] for f in chromo['fields']), resource_id))
        record_data_dict = result['records'][0]

        assert record_data_dict['contract_value'] == Decimal('10000.00')
        assert record_data_dict['original_value'] == Decimal('10000.00')
        assert record_data_dict['amendment_value'] == Decimal('100000.00')

        record_data_dict['contract_date'] = '2018-12-25'  # old date for conditional amendment_value
        record_data_dict['contract_value'] = '10000.00999'
        record_data_dict['original_value'] = None
        record_data_dict['amendment_value'] = ''

        self.sys_action.datastore_upsert(
            resource_id=resource_id,
            records=[record_data_dict])

        result = self.sys_action.datastore_search_sql(
            sql="SELECT %s from \"%s\"" % (', '.join(f['datastore_id'] for f in chromo['fields']), resource_id))
        record_data_dict = result['records'][0]

        assert record_data_dict['contract_value'] == Decimal('10000.01')
        assert not record_data_dict['original_value']
        assert not record_data_dict['amendment_value']
