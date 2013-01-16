import unittest

import paste.fixture
import pylons.test

from ckanext.canada.package_form import build_canada_package_form


class TestBuildCanadaPackageForm(unittest.TestCase):
    @classmethod
    def setupClass(cls):
        # The app object is a wrapper around the CKAN web application, with
        # methods for making testing convenient.
        # See http://pythonpaste.org/testing-applications.html
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)

    def setUp(self):
        self.b = build_canada_package_form(False, [])

    def test_package_form_is_sane(self):
        self.assertTrue(self.b)

