# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckanext.canada.tests.factories import (
    CanadaDataset as Dataset,
    CanadaResource as Resource)

from ckanext.canada.commands import _trim_package, PACKAGE_TRIM_FIELDS, RESOURCE_TRIM_FIELDS


class TestTrimPackage(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestTrimPackage, self).setup_method(method)

        self.example_pkg = Dataset()
        resources = []
        for _i in range(6):
            resources.append(Resource(
                package_id=self.example_pkg['id']))
        self.example_pkg['resources'] = resources
        _trim_package(self.example_pkg)


    def test_trimmed_dataset(self):
        for field in PACKAGE_TRIM_FIELDS:
            assert field not in self.example_pkg
        assert 'type' in self.example_pkg
        assert 'name' in self.example_pkg and self.example_pkg['name'] is not None
        assert 'state' in self.example_pkg


    def test_trimmed_resources(self):
        for resource in self.example_pkg['resources']:
            for field in RESOURCE_TRIM_FIELDS:
                assert field not in resource
                assert 'size' in resource
                assert 'name' in resource
