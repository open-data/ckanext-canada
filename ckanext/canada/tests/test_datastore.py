# -*- coding: UTF-8 -*-
import logging
import mock
import io
from ckanext.canada.tests import CanadaTestBase
from ckan import plugins
from ckan.lib.uploader import ResourceUpload
from ckan.tests.helpers import change_config

from frictionless.system.loader import Loader
import pytest
from ckanext.canada.tests.factories import (
    CanadaResource as Resource,
)
from ckanext.canada.tests.helpers import (
    MockFieldStorage,
    get_sample_filepath,
)
# type_ignore_reason: custom fixtures
from ckanext.canada.tests.fixtures import (
    mock_uploads,  # type: ignore
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


    def _setup_resource_upload(self, filename):
        csv_filepath = get_sample_filepath(filename)

        fake_file_obj = io.BytesIO()

        with open(csv_filepath, 'rb') as f:
            file_data = f.read()
            fake_file_obj.write(file_data)
            mock_field_store = MockFieldStorage(fake_file_obj, filename)
            resource = Resource(url='__upload',
                                url_type='upload',
                                format='CSV',
                                upload=mock_field_store)

            fake_stream = io.BufferedReader(io.BytesIO(file_data))

        return resource, fake_stream


    @change_config('ckanext.validation.run_on_create_async', False)
    @change_config('ckanext.validation.run_on_update_async', False)
    @change_config('ckanext.validation.locales_offered', 'en')
    @change_config('ckanext.validation.static_validation_options', '{"checks":[{"type":"baseline"},{"type":"ds-headers"}]}')
    @pytest.mark.usefixtures("mock_uploads")
    @mock.patch('ckanext.validation.jobs.get_resource_uploader', mock_get_resource_uploader)
    def test_validation_report(self, mock_uploads):
        resource, fake_stream = self._setup_resource_upload('sample.csv')

        with mock.patch('io.open', return_value=fake_stream):

            run_validation_job(resource)

        report = self.action.resource_validation_show(resource_id=resource.get('id'))

        assert report.get('status') == 'success'
        assert 'language' in report
        assert report.get('language') == 'en'


    @change_config('ckanext.validation.run_on_create_async', False)
    @change_config('ckanext.validation.run_on_update_async', False)
    @change_config('ckanext.validation.locales_offered', 'en')
    @change_config('ckanext.validation.static_validation_options', '{"checks":[{"type":"baseline"},{"type":"ds-headers"}]}')
    @pytest.mark.usefixtures("mock_uploads")
    @mock.patch('ckanext.validation.jobs.get_resource_uploader', mock_get_resource_uploader)
    def test_validation_report_bad_ds_headers(self, mock_uploads):
        resource, fake_stream = self._setup_resource_upload('sample_with_bad_ds_headers.csv')

        with mock.patch('io.open', return_value=fake_stream):

            run_validation_job(resource)

        report = self.action.resource_validation_show(resource_id=resource.get('id'))

        assert report.get('status') == 'failure'
        assert 'language' in report
        assert report.get('language') == 'en'
        report = report.get('report', {})
        assert report.get('stats', {}).get('errors') == 2
        tasks = report.get('tasks', [])
        assert len(tasks) == 1
        errors = tasks[0].get('errors')
        assert  len(errors) == 2
        assert errors[0].get('type') == 'datastore-invalid-header'
        assert '_thisisnotallowed' in errors[0].get('note')
        assert errors[1].get('type') == 'datastore-header-too-long'
        assert 'thisheaderisgoingtobewaywaywaywaywaywaywaywaywaywaywaywaywaywaywaywaywaywaywaywaywaywaytolongforthedatastore' in errors[1].get('note')


    @change_config('ckanext.validation.run_on_create_async', False)
    @change_config('ckanext.validation.run_on_update_async', False)
    @change_config('ckanext.validation.locales_offered', 'en')
    @change_config('ckanext.validation.static_validation_options', '{"skip_errors":["blank-row"],"checks":[{"type":"baseline"},{"type":"ds-headers"}]}')
    @pytest.mark.usefixtures("mock_uploads")
    @mock.patch('ckanext.validation.jobs.get_resource_uploader', mock_get_resource_uploader)
    def test_validation_report_empty_lines(self, mock_uploads):
        resource, fake_stream = self._setup_resource_upload('sample_with_empty_lines.csv')

        with mock.patch('io.open', return_value=fake_stream):

            run_validation_job(resource)

        report = self.action.resource_validation_show(resource_id=resource.get('id'))

        assert report.get('status') == 'success'
        assert 'language' in report
        assert report.get('language') == 'en'


    @change_config('ckanext.validation.run_on_create_async', False)
    @change_config('ckanext.validation.run_on_update_async', False)
    @change_config('ckanext.validation.locales_offered', 'en')
    @change_config('ckanext.validation.static_validation_options', '{"checks":[{"type":"baseline"},{"type":"ds-headers"}]}')
    @pytest.mark.usefixtures("mock_uploads")
    @mock.patch('ckanext.validation.jobs.get_resource_uploader', mock_get_resource_uploader)
    def test_validation_report_white_space(self, mock_uploads):
        resource, fake_stream = self._setup_resource_upload('sample_with_extra_white_space.csv')

        with mock.patch('io.open', return_value=fake_stream):

            run_validation_job(resource)

        report = self.action.resource_validation_show(resource_id=resource.get('id'))

        assert report.get('status') == 'success'
        assert 'language' in report
        assert report.get('language') == 'en'


    @change_config('ckanext.validation.run_on_create_async', False)
    @change_config('ckanext.validation.run_on_update_async', False)
    @change_config('ckanext.validation.locales_offered', 'en fr')
    @change_config('ckanext.validation.static_validation_options', '{"checks":[{"type":"baseline"},{"type":"ds-headers"}]}')
    @pytest.mark.usefixtures("mock_uploads")
    @mock.patch('ckanext.validation.jobs.get_resource_uploader', mock_get_resource_uploader)
    def test_validation_report_languages(self, mock_uploads):
        resource, fake_stream = self._setup_resource_upload('sample.csv')

        def mocked_byte_stream(cls):
            return fake_stream

        with mock.patch('io.open', return_value=fake_stream):

            with mock.patch.object(Loader, 'read_byte_stream', mocked_byte_stream):

                with mock.patch.object(Loader, 'buffer', fake_stream):

                    #FIXME: issue with secondary language validation getting: I/O operation on closed file

                    run_validation_job(resource)

        report = self.action.resource_validation_show(resource_id=resource.get('id'), lang='en')

        assert len(report.get('report', {}).get('tasks', [])) == 1
        assert 'language' in report
        assert report.get('language') == 'en'

        report = self.action.resource_validation_show(resource_id=resource.get('id'), lang='fr')

        assert len(report.get('report', {}).get('tasks', [])) == 1
        assert 'language' in report
        assert report.get('language') == 'fr'


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


    def _get_ds_records(self, exclude_field_schemas=True):
        result = self.action.datastore_search(resource_id=self.resource_id)
        ds_info = self.action.datastore_info(id=self.resource_id)
        if exclude_field_schemas:
            for field in ds_info.get('fields'):
                field.pop('schema', None)
        return ds_info.get('fields'), result.get('records')


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
            {'type': 'timestamp', 'id': 'date'},
            {'type': 'numeric', 'id': 'temperature'},
            {'type': 'text', 'id': 'place'}
        ]

        expected_records = [
            {"_id": 1, "date": "2011-01-01T00:00:00", "temperature": 1, "place": "Galway"},
            {"_id": 2, "date": "2011-01-02T00:00:00", "temperature": -1, "place": "Galway"},
            {"_id": 3, "date": "2011-01-03T00:00:00", "temperature": 0, "place": "Galway"},
            {"_id": 4, "date": "2011-01-01T00:00:00", "temperature": 6, "place": "Berkeley"},
            {"_id": 5, "date": None, "temperature": None, "place": "Berkeley"},
            {"_id": 6, "date": "2011-01-03T00:00:00", "temperature": 5, "place": ""}
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
            {'type': 'timestamp', 'id': 'date'},
            {'type': 'numeric', 'id': 'temperature'},
            {'type': 'text', 'id': 'place'}
        ]

        expected_records = [
            {"_id": 1, "date": "2011-01-01T00:00:00", "temperature": 1, "place": "Galway"},
            {"_id": 2, "date": "2011-01-02T00:00:00", "temperature": -1, "place": "Galway"},
            {"_id": 3, "date": "2011-01-03T00:00:00", "temperature": 0, "place": "Galway"},
            {"_id": 4, "date": "2011-01-01T00:00:00", "temperature": 6, "place": "Berkeley"},
            {"_id": 5, "date": None, "temperature": None, "place": "Berkeley"},
            {"_id": 6, "date": "2011-01-03T00:00:00", "temperature": 5, "place": ""}
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
            {'type': 'timestamp', 'id': 'date'},
            {'type': 'numeric', 'id': 'temperature'},
            {'type': 'text', 'id': 'place'}
        ]

        expected_records = [
            {"_id": 1, "date": "2011-01-01T00:00:00", "temperature": 1, "place": "Galway"},
            {"_id": 2, "date": "2011-01-02T00:00:00", "temperature": -1, "place": "Galway"},
            {"_id": 3, "date": "2011-01-03T00:00:00", "temperature": 0, "place": "Galway"},
            {"_id": 4, "date": "2011-01-01T00:00:00", "temperature": 6, "place": "Berkeley"},
            {"_id": 5, "date": None, "temperature": None, "place": "Berkeley"},
            {"_id": 6, "date": "2011-01-03T00:00:00", "temperature": 5, "place": ""}
        ]

        assert fields == expected_fields
        assert records == expected_records
