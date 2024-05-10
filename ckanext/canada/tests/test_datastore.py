# -*- coding: UTF-8 -*-
import logging
import mock
from cgi import FieldStorage
from ckanext.canada.tests import CanadaTestBase
from ckan import plugins
from ckan.lib.uploader import ResourceUpload
from ckan.tests.helpers import change_config

import pytest
from ckanext.canada.tests.factories import (
    CanadaResource as Resource,
    MockFieldStorage,
    get_sample_filepath,
    mock_uploads,
)
from ckanext.xloader import loader
from ckanext.xloader.job_exceptions import LoaderError
from ckanext.validation.jobs import run_validation_job

from ckanapi import LocalCKAN

logger = logging.getLogger(__name__)


class MockUploader(ResourceUpload):
    def get_path(self, resource_id):
        return '/tmp/example/{}'.format(resource_id)


def mock_get_resource_uploader(data_dict):
    return MockUploader(data_dict)


class TestDatastoreValidation(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestDatastoreValidation, self).setup_method(method)

        if plugins.plugin_loaded('xloader'):
            plugins.unload('xloader')

        if plugins.plugin_loaded('cloudstorage'):
            plugins.unload('cloudstorage')

        if not plugins.plugin_loaded('validation'):
            plugins.load('validation')

        self.action = LocalCKAN().action


    @classmethod
    def teardown_method(self):
        """Method is called at class level after EACH test methods of the class are called.
        Close any state specific to the execution of the given class methods.
        """
        if plugins.plugin_loaded('xloader'):
            plugins.unload('xloader')

        if plugins.plugin_loaded('cloudstorage'):
            plugins.unload('cloudstorage')

        if not plugins.plugin_loaded('validation'):
            plugins.load('validation')


    @change_config('ckanext.validation.run_on_create_async', False)
    @change_config('ckanext.validation.run_on_update_async', False)
    @mock_uploads
    @mock.patch('ckanext.validation.jobs.get_resource_uploader', mock_get_resource_uploader)
    def test_validation_report(self, mock_open):
        csv_filepath = get_sample_filepath("sample.csv")

        with open(csv_filepath, 'r') as f:
            resource = Resource(url='__upload',
                                url_type='upload',
                                format='CSV',
                                upload=MockFieldStorage(f, 'sample.csv'))

        run_validation_job(resource)

        report = self.action.resource_validation_show(resource_id=resource.get('id'))

        logger.info("    ")
        logger.info("DEBUGGING::")
        logger.info("    ")
        logger.info(report)
        logger.info("    ")
        assert False


class TestDatastoreXloader(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestDatastoreXloader, self).setup_method(method)

        if not plugins.plugin_loaded('xloader'):
            plugins.load('xloader')

        if plugins.plugin_loaded('validation'):
            plugins.unload('validation')

        self.action = LocalCKAN().action

        resource = Resource()
        self.resource_id = resource['id']


    @classmethod
    def teardown_method(self):
        """Method is called at class level after EACH test methods of the class are called.
        Close any state specific to the execution of the given class methods.
        """
        if plugins.plugin_loaded('xloader'):
            plugins.unload('xloader')

        if not plugins.plugin_loaded('validation'):
            plugins.load('validation')


    def _get_ds_records(self):
        result = self.action.datastore_search(resource_id=self.resource_id)
        return result.get('fields'), result.get('records')


    def test_load_csv(self):
        csv_filepath = get_sample_filepath("sample.csv")

        loader.load_csv(
            csv_filepath,
            resource_id=self.resource_id,
            mimetype="text/csv",
            logger=logger,
        )

        fields, records = self._get_ds_records()

        expected_fields = [
            {'type': 'int', 'id': '_id'},
            {'type': 'text', 'id': 'date'},
            {'type': 'text', 'id': 'temperature'},
            {'type': 'text', 'id': 'place'}
        ]

        expected_records = [
            {"_id": 1, "date": "2011-01-01", "temperature": "1", "place": "Galway"},
            {"_id": 2, "date": "2011-01-02", "temperature": "-1", "place": "Galway"},
            {"_id": 3, "date": "2011-01-03", "temperature": "0", "place": "Galway"},
            {"_id": 4, "date": "2011-01-01", "temperature": "6", "place": "Berkeley"},
            {"_id": 5, "date": None, "temperature": None, "place": "Berkeley"},
            {"_id": 6, "date": "2011-01-03", "temperature": "5", "place": None}
        ]

        assert fields == expected_fields
        assert records == expected_records


    def test_load_table(self):
        csv_filepath = get_sample_filepath("sample.csv")

        loader.load_table(
            csv_filepath,
            resource_id=self.resource_id,
            mimetype="text/csv",
            logger=logger,
        )

        fields, records = self._get_ds_records()

        expected_fields = [
            {'type': 'int', 'id': '_id'},
            {'info': {'type_override': 'timestamp'}, 'type': 'timestamp', 'id': 'date'},
            {'type': 'text', 'id': 'temperature'},
            {'type': 'text', 'id': 'place'}
        ]

        expected_records = [
            {"_id": 1, "date": "2011-01-01T00:00:00", "temperature": "1", "place": "Galway"},
            {"_id": 2, "date": "2011-01-02T00:00:00", "temperature": "-1", "place": "Galway"},
            {"_id": 3, "date": "2011-01-03T00:00:00", "temperature": "0", "place": "Galway"},
            {"_id": 4, "date": "2011-01-01T00:00:00", "temperature": "6", "place": "Berkeley"},
            {"_id": 5, "date": None, "temperature": "", "place": "Berkeley"},
            {"_id": 6, "date": "2011-01-03T00:00:00", "temperature": "5", "place": ""}
        ]

        assert fields == expected_fields
        assert records == expected_records


    def test_load_csv_bad_ds_headers(self):
        csv_filepath = get_sample_filepath("sample_with_bad_ds_headers.csv")

        with pytest.raises(LoaderError) as le:
            loader.load_csv(
                csv_filepath,
                resource_id=self.resource_id,
                mimetype="text/csv",
                logger=logger,
            )

        assert '"_thisisnotallowed" is not a valid field name' in str(le)


    def test_load_table_bad_ds_headers(self):
        csv_filepath = get_sample_filepath("sample_with_bad_ds_headers.csv")

        with pytest.raises(LoaderError) as le:
            loader.load_table(
                csv_filepath,
                resource_id=self.resource_id,
                mimetype="text/csv",
                logger=logger,
            )

        assert '"_thisisnotallowed" is not a valid field name' in str(le)


    def test_load_csv_empty_lines(self):
        csv_filepath = get_sample_filepath("sample_with_empty_lines.csv")

        loader.load_csv(
            csv_filepath,
            resource_id=self.resource_id,
            mimetype="text/csv",
            logger=logger,
        )

        fields, records = self._get_ds_records()

        expected_fields = [
            {'type': 'int', 'id': '_id'},
            {'type': 'text', 'id': 'date'},
            {'type': 'text', 'id': 'temperature'},
            {'type': 'text', 'id': 'place'}
        ]

        expected_records = [
            {"_id": 1, "date": "2011-01-01", "temperature": "1", "place": "Galway"},
            {"_id": 2, "date": "2011-01-02", "temperature": "-1", "place": "Galway"},
            {"_id": 3, "date": "2011-01-03", "temperature": "0", "place": "Galway"},
            {"_id": 4, "date": "2011-01-01", "temperature": "6", "place": "Berkeley"},
            {"_id": 5, "date": None, "temperature": None, "place": "Berkeley"},
            {"_id": 6, "date": "2011-01-03", "temperature": "5", "place": None}
        ]

        assert fields == expected_fields
        assert records == expected_records


    def test_load_table_empty_lines(self):
        csv_filepath = get_sample_filepath("sample_with_empty_lines.csv")

        loader.load_table(
            csv_filepath,
            resource_id=self.resource_id,
            mimetype="text/csv",
            logger=logger,
        )

        fields, records = self._get_ds_records()

        expected_fields = [
            {'type': 'int', 'id': '_id'},
            {'info': {'type_override': 'timestamp'}, 'type': 'timestamp', 'id': 'date'},
            {'type': 'text', 'id': 'temperature'},
            {'type': 'text', 'id': 'place'}
        ]

        expected_records = [
            {"_id": 1, "date": "2011-01-01T00:00:00", "temperature": "1", "place": "Galway"},
            {"_id": 2, "date": "2011-01-02T00:00:00", "temperature": "-1", "place": "Galway"},
            {"_id": 3, "date": "2011-01-03T00:00:00", "temperature": "0", "place": "Galway"},
            {"_id": 4, "date": "2011-01-01T00:00:00", "temperature": "6", "place": "Berkeley"},
            {"_id": 5, "date": None, "temperature": "", "place": "Berkeley"},
            {"_id": 6, "date": "2011-01-03T00:00:00", "temperature": "5", "place": ""}
        ]

        assert fields == expected_fields
        assert records == expected_records


    def test_load_csv_white_space(self):
        csv_filepath = get_sample_filepath("sample_with_extra_white_space.csv")

        loader.load_csv(
            csv_filepath,
            resource_id=self.resource_id,
            mimetype="text/csv",
            logger=logger,
        )

        fields, records = self._get_ds_records()

        expected_fields = [
            {'type': 'int', 'id': '_id'},
            {'type': 'text', 'id': 'date'},
            {'type': 'text', 'id': 'temperature'},
            {'type': 'text', 'id': 'place'}
        ]

        expected_records = [
            {"_id": 1, "date": "2011-01-01", "temperature": "1", "place": "Galway"},
            {"_id": 2, "date": "2011-01-02", "temperature": "-1", "place": "Galway"},
            {"_id": 3, "date": "2011-01-03", "temperature": "0", "place": "Galway"},
            {"_id": 4, "date": "2011-01-01", "temperature": "6", "place": "Berkeley"},
            {"_id": 5, "date": None, "temperature": None, "place": "Berkeley"},
            {"_id": 6, "date": "2011-01-03", "temperature": "5", "place": None}
        ]

        logger.info("    ")
        logger.info("DEBUGGING::")
        logger.info("    ")
        logger.info(records)
        logger.info("    ")
        # assert False

        assert fields == expected_fields
        assert records == expected_records


    def test_load_table_white_space(self):
        csv_filepath = get_sample_filepath("sample_with_extra_white_space.csv")

        loader.load_table(
            csv_filepath,
            resource_id=self.resource_id,
            mimetype="text/csv",
            logger=logger,
        )

        fields, records = self._get_ds_records()

        expected_fields = [
            {'type': 'int', 'id': '_id'},
            {'info': {'type_override': 'timestamp'}, 'type': 'timestamp', 'id': 'date'},
            {'type': 'text', 'id': 'temperature'},
            {'type': 'text', 'id': 'place'}
        ]

        expected_records = [
            {"_id": 1, "date": "2011-01-01T00:00:00", "temperature": "1", "place": "Galway"},
            {"_id": 2, "date": "2011-01-02T00:00:00", "temperature": "-1", "place": "Galway"},
            {"_id": 3, "date": "2011-01-03T00:00:00", "temperature": "0", "place": "Galway"},
            {"_id": 4, "date": "2011-01-01T00:00:00", "temperature": "6", "place": "Berkeley"},
            {"_id": 5, "date": None, "temperature": "", "place": "Berkeley"},
            {"_id": 6, "date": "2011-01-03T00:00:00", "temperature": "5", "place": ""}
        ]

        assert fields == expected_fields
        assert records == expected_records
