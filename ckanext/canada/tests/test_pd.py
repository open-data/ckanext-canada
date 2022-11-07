# -*- coding: UTF-8 -*-
from ckanext.canada.pd import dollar_range_facet


class TestDollarRangeFacet(object):
    def test_too_low(self):
        assert dollar_range_facet('foo', [100, 500, 1000], 50) == {}


    def test_negative(self):
        assert dollar_range_facet('foo', [100, 500, 1000], -500) == {}


    def test_top_bucket(self):
        assert dollar_range_facet('foo', [100, 500, 1000], 5000) == {
           'foo_range': u'2',
            'foo_en': u'A: $1,000.00+',
            'foo_fr': u'A: 1\u202f000,00\xa0$ +'}


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
