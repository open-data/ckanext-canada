# -*- coding: UTF-8 -*-
from ckanext.canada.pd import dollar_range_facet
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN

from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo
from ckanext.canada.pd import _update_records, clear_index, solr_connection


class TestDollarRangeFacet(object):
    def test_too_low(self):
        assert dollar_range_facet('foo', [100, 500, 1000], 50) == {}


    def test_negative(self):
        assert dollar_range_facet('foo', [100, 500, 1000], -500) == {}


    def test_top_bucket(self):
        assert dollar_range_facet('foo', [100, 500, 1000], 5000) == {
            'foo_range': u'2',
            'foo_en': u'A: $1,000.00+',
            'foo_fr': u'A: 1\xa0000,00\xa0$ +'}


    def test_bucket_0_bottom_edge(self):
        assert dollar_range_facet('foo', [100, 500, 1000], 100) == {
            'foo_range': u'0',
            'foo_en': u'C: $100.00 - $499.99',
            'foo_fr': u'C: 100,00\xa0$ - 499,99\xa0$'}


    def test_bucket_1_top_edge(self):
        assert dollar_range_facet('foo', [100, 500, 1000], 999.999) == {
           'foo_range': u'1',
            'foo_en': u'B: $500.00 - $999.99',
            'foo_fr': u'B: 500,00\xa0$ - 999,99\xa0$'}


class TestIndex(CanadaTestBase):

    ds_type = 'ati'

    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestIndex, self).setup_method(method)

        self.org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type=self.ds_type, owner_org=self.org['name'])
        rval = self.lc.action.recombinant_show(dataset_type=self.ds_type, owner_org=self.org['name'])

        self.resource_id = rval['resources'][0]['id']


    def get_records(self):
        rval = self.lc.action.datastore_search(
            resource_id=self.resource_id,
            limit=25000,
            offset=0)
        records = rval['records']
        return records


    def test_max_text_length(self):
        record = get_chromo(self.ds_type)['examples']['record']
        record['summary_en'] = 'e' * 33000
        record['summary_fr'] = 'é' * 33000
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

        clear_index(self.ds_type)
        conn = solr_connection(self.ds_type)

        org_detail = self.lc.action.organization_show(id=self.org['id'])
        resource = self.lc.action.resource_show(id=self.resource_id)

        _update_records(self.get_records(), org_detail, conn, resource['name'], None, retry=False)

        conn.commit()
