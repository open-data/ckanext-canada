# -*- coding: UTF-8 -*-
import pytest
from sqlalchemy.exc import IntegrityError
import mock
import io
import re

from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN
from ckan import model
from ckan.model.types import make_uuid
import ckan.lib.uploader as uploader

from ckanext.canada.tests.factories import (
    CanadaResource as Resource,
    CanadaOrganization as Organization,
    CanadaUser as User,
    CanadaSysadminWithToken as Sysadmin
)
from ckanext.canada.tests.helpers import (
    MockFieldStorage,
    get_sample_filepath,
)
# type_ignore_reason: custom fixtures
from ckanext.canada.tests.fixtures import (  # noqa: F401
    mock_uploads,  # type: ignore
)


class TestCanadaLogic(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestCanadaLogic, self).setup_class()

        self.lc = LocalCKAN()

    def test_data_dictionary(self):
        """
        The custom fields should get saved in the Data Dictionary,
        and be returned from datastore_info.
        """
        resource = Resource()
        self.lc.action.datastore_create(resource_id=resource['id'],
                                        force=True,
                                        fields=[{'id': 'exampled_id',
                                                 'type': 'text',
                                                 'info': {'label_en': 'Example Label',
                                                          'label_fr': 'Example Label FR',
                                                          'notes_en': 'Example Description',
                                                          'notes_fr': 'Example Description FR'}}])

        ds_info = self.lc.action.datastore_info(id=resource['id'])

        assert 'fields' in ds_info
        assert len(ds_info['fields']) == 1
        assert ds_info['fields'][0]['id'] == 'exampled_id'
        assert 'info' in ds_info['fields'][0]
        assert 'label_en' in ds_info['fields'][0]['info']
        assert ds_info['fields'][0]['info']['label_en'] == 'Example Label'
        assert 'label_fr' in ds_info['fields'][0]['info']
        assert ds_info['fields'][0]['info']['label_fr'] == 'Example Label FR'
        assert 'notes_en' in ds_info['fields'][0]['info']
        assert ds_info['fields'][0]['info']['notes_en'] == 'Example Description'
        assert 'notes_fr' in ds_info['fields'][0]['info']
        assert ds_info['fields'][0]['info']['notes_fr'] == 'Example Description FR'


class TestMetadataDatesLogic(CanadaTestBase):
    """
    Tests the schema and logic behind Package and Resource metadata_created
    and metadata_modified fields.

    Note:
        Package:    metadata_created (set by sysadmins)
                    metadata_modified (set by sysadmins)

        Resource:   last_modified (e.g. the external URL or upload) (set by anyone)
                    created (e.g. the date of file creation) (set by anyone)
                    metadata_modified (set by sysadmins)
    """

    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestMetadataDatesLogic, self).setup_class()

        sysadmin = Sysadmin()
        editor = User()
        org = Organization(users=[{
            'name': sysadmin['name'],
            'capacity': 'admin'},
           {'name': editor['name'],
            'capacity': 'editor'}])
        self.sysadmin_action = LocalCKAN(username=sysadmin['name']).action
        self.editor_action = LocalCKAN(username=editor['name']).action

        self.create_date = '1994-01-01T00:00:01'  # .000000
        self.update_date = '1997-01-01T00:00:01'  # .000000

        self.pkg_dict = {
            'type': 'dataset',
            'owner_org': org['name'],
            'collection': 'primary',
            'title_translated': {'en': 'A Novel By Tolstoy',
                                 'fr': 'Un novel par Tolstoy'},
            'frequency': 'as_needed',
            'notes_translated': {'en': '...', 'fr': '...'},
            'subject': ['persons'],
            'date_published': '2013-01-01',
            'keywords': {'en': ['book'], 'fr': ['livre']},
            'license_id': 'ca-ogl-lgo',
            'ready_to_publish': 'true',
            'imso_approval': 'true',
            'jurisdiction': 'federal',
            'maintainer_email': 'not@all.example.com',
            'restrictions': 'unrestricted',
            'metadata_created': self.create_date,
            'metadata_modified': self.create_date,
            'resources': [{
                'name_translated': {'en': 'Full text.', 'fr': 'Full text.'},
                'format': 'TXT',
                'url': 'http://www.annakarenina.com/download/',
                'size': 42,
                'resource_type': 'dataset',
                'language': ['zxx'],
                'created': self.create_date,
                'last_modified': self.create_date,
                'metadata_modified': self.create_date,
            }],
        }

    def test_package_create_metadata_fields(self):
        """
        When creating packages, sysadmins should be able to provide
        a metadata_created value
        """
        pkg = self.editor_action.package_create(
            name='12345678-9abc-def0-1234-56789abcdeb7',
            **self.pkg_dict)

        # sysadmin only field
        assert pkg['metadata_created'] != self.create_date
        # sysadmin only field
        assert pkg['metadata_modified'] != self.create_date
        # can be edited by permissioned users, e.g. editors
        assert pkg['resources'][0]['created'] == self.create_date
        # can be edited by permissioned users, e.g. editors
        assert pkg['resources'][0]['last_modified'] == self.create_date
        # sysadmin only field
        assert pkg['resources'][0]['metadata_modified'] != self.create_date

        pkg = self.sysadmin_action.package_create(
            name='12345678-9abc-def0-1234-56789abcdec9',
            **self.pkg_dict)

        assert pkg['metadata_created'] == self.create_date
        assert pkg['metadata_modified'] == self.create_date
        assert pkg['resources'][0]['created'] == self.create_date
        assert pkg['resources'][0]['last_modified'] == self.create_date
        assert pkg['resources'][0]['metadata_modified'] == self.create_date

    def test_package_update_metadata_fields(self):
        """
        When updating packages, sysadmins should be able to provide
        a metadata_updated and metadata_created value
        """
        pkg = self.editor_action.package_create(
            name='12345678-9abc-def0-1234-56789abcd20d',
            **self.pkg_dict)

        pkg['metadata_created'] = self.update_date
        pkg['metadata_modified'] = self.update_date
        pkg['resources'][0]['created'] = self.update_date
        pkg['resources'][0]['last_modified'] = self.update_date
        pkg['resources'][0]['metadata_modified'] = self.update_date

        pkg = self.editor_action.package_update(**pkg)

        # sysadmin only field
        assert pkg['metadata_created'] != self.update_date
        # sysadmin only field
        assert pkg['metadata_modified'] != self.update_date
        # can be edited by permissioned users, e.g. editors
        assert pkg['resources'][0]['created'] == self.update_date
        # can be edited by permissioned users, e.g. editors
        assert pkg['resources'][0]['last_modified'] == self.update_date
        # sysadmin only field
        assert pkg['resources'][0]['metadata_modified'] != self.update_date

        pkg = self.sysadmin_action.package_create(
            name='12345678-9abc-def0-1234-56789abcdc81',
            **self.pkg_dict)

        pkg['metadata_created'] = self.update_date
        pkg['metadata_modified'] = self.update_date
        pkg['resources'][0]['created'] = self.update_date
        pkg['resources'][0]['last_modified'] = self.update_date
        pkg['resources'][0]['metadata_modified'] = self.update_date

        pkg = self.sysadmin_action.package_update(**pkg)

        assert pkg['metadata_created'] == self.update_date
        assert pkg['metadata_modified'] == self.update_date
        assert pkg['resources'][0]['created'] == self.update_date
        assert pkg['resources'][0]['last_modified'] == self.update_date
        assert pkg['resources'][0]['metadata_modified'] == self.update_date

    def test_package_patch_metadata_fields(self):
        """
        When patching packages and resources, sysadmins should be
        able to provide a metadata_updated and metadata_created value
        """
        pkg = self.editor_action.package_create(
            name='12345678-9abc-def0-1234-56789abcd34c',
            **self.pkg_dict)

        pkg = self.editor_action.package_patch(
            id=pkg['id'],
            metadata_created=self.update_date,
            metadata_modified=self.update_date)

        # sysadmin only field
        assert pkg['metadata_created'] != self.update_date
        # sysadmin only field
        assert pkg['metadata_modified'] != self.update_date

        res = self.editor_action.resource_patch(
            id=pkg['resources'][0]['id'],
            created=self.update_date,
            last_modified=self.update_date,
            metadata_modified=self.update_date)

        # can be edited by permissioned users, e.g. editors
        assert res['created'] == self.update_date
        # can be edited by permissioned users, e.g. editors
        assert res['last_modified'] == self.update_date
        # sysadmin only field
        assert res['metadata_modified'] != self.update_date

        pkg = self.sysadmin_action.package_create(
            name='12345678-9abc-def0-1234-56789abcef89',
            **self.pkg_dict)

        pkg = self.sysadmin_action.package_patch(
            id=pkg['id'],
            metadata_created=self.update_date,
            metadata_modified=self.update_date)

        assert pkg['metadata_created'] == self.update_date
        assert pkg['metadata_modified'] == self.update_date

        res = self.sysadmin_action.resource_patch(
            id=pkg['resources'][0]['id'],
            created=self.update_date,
            last_modified=self.update_date,
            metadata_modified=self.update_date)

        assert res['created'] == self.update_date
        assert res['last_modified'] == self.update_date
        assert res['metadata_modified'] == self.update_date


class TestResourcePositionLogic(CanadaTestBase):
    """
    Tests that adding, updating, and patching Resources respect their
    original position and do not magically get deleted.
    """

    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestResourcePositionLogic, self).setup_class()

        sysadmin = Sysadmin()
        org = Organization(users=[{
            'name': sysadmin['name'],
            'capacity': 'admin'},])
        self.sysadmin_action = LocalCKAN(username=sysadmin['name']).action

        self.res_dict = {
            'name_translated': {'en': 'Full text.', 'fr': 'Full text.'},
            'format': 'TXT',
            'url': 'http://www.annakarenina.com/download/',
            'size': 42,
            'resource_type': 'dataset',
            'language': ['zxx'],
            'created': '1994-01-01T00:00:01',
            'last_modified': '1994-01-01T00:00:01',
            'metadata_modified': '1994-01-01T00:00:01',
        }

        self.pkg_dict = {
            'type': 'dataset',
            'owner_org': org['name'],
            'collection': 'primary',
            'title_translated': {'en': 'A Novel By Tolstoy',
                                 'fr': 'Un novel par Tolstoy'},
            'frequency': 'as_needed',
            'notes_translated': {'en': '...', 'fr': '...'},
            'subject': ['persons'],
            'date_published': '2013-01-01',
            'keywords': {'en': ['book'], 'fr': ['livre']},
            'license_id': 'ca-ogl-lgo',
            'ready_to_publish': 'true',
            'imso_approval': 'true',
            'jurisdiction': 'federal',
            'maintainer_email': 'not@all.example.com',
            'restrictions': 'unrestricted',
            'metadata_created': '1994-01-01T00:00:01',
            'metadata_modified': '1994-01-01T00:00:01',
        }

    def _new_res(self):
        return dict(self.res_dict, id=make_uuid())

    def test_auto_resource_positions(self):
        """
        Creating new Resources should just add them to the list of resources.
        """
        pkg = self.sysadmin_action.package_create(
            name='76545678-9abc-def0-1234-56789abcd34c',
            resources=[self._new_res()],
            **self.pkg_dict)

        assert len(pkg['resources']) == 1
        assert pkg['resources'][0]['position'] == 0

        self.sysadmin_action.resource_create(
            package_id=pkg['id'],
            **self._new_res())

        pkg = self.sysadmin_action.package_show(id=pkg['id'])

        assert len(pkg['resources']) == 2
        assert pkg['resources'][0]['position'] == 0
        assert pkg['resources'][1]['position'] == 1

    def test_updating_resource_same_position(self):
        """
        Updating a resource should keep its previous position
        """
        pkg = self.sysadmin_action.package_create(
            name='76545678-7ade-def0-1234-56789abcd34c',
            resources=[self._new_res(), self._new_res(), self._new_res(),
                       self._new_res(), self._new_res(), self._new_res()],
            **self.pkg_dict)

        assert len(pkg['resources']) == 6
        assert pkg['resources'][0]['position'] == 0
        assert pkg['resources'][1]['position'] == 1
        assert pkg['resources'][2]['position'] == 2
        assert pkg['resources'][3]['position'] == 3
        assert pkg['resources'][4]['position'] == 4
        assert pkg['resources'][5]['position'] == 5

        res_dict = pkg['resources'][3].copy()
        res_dict['name_translated'] = {'en': 'UPDATED', 'fr': 'UPDATED'}

        self.sysadmin_action.resource_update(**res_dict)

        pkg = self.sysadmin_action.package_show(id=pkg['id'])

        assert len(pkg['resources']) == 6
        assert pkg['resources'][0]['position'] == 0
        assert pkg['resources'][1]['position'] == 1
        assert pkg['resources'][2]['position'] == 2
        assert pkg['resources'][3]['position'] == 3
        assert pkg['resources'][3]['name_translated'] == {'en': 'UPDATED', 'fr': 'UPDATED'}
        assert pkg['resources'][4]['position'] == 4
        assert pkg['resources'][5]['position'] == 5

        # you cannot update the position via update actions
        res_dict = pkg['resources'][1].copy()
        res_dict['name_translated'] = {'en': 'UPDATED AGAIN', 'fr': 'UPDATED AGAIN'}
        res_dict['position'] = 99

        self.sysadmin_action.resource_update(**res_dict)

        pkg = self.sysadmin_action.package_show(id=pkg['id'])

        assert len(pkg['resources']) == 6
        assert pkg['resources'][0]['position'] == 0
        assert pkg['resources'][1]['position'] == 1
        assert pkg['resources'][1]['position'] != 99
        assert pkg['resources'][1]['name_translated'] == {'en': 'UPDATED AGAIN', 'fr': 'UPDATED AGAIN'}
        assert pkg['resources'][2]['position'] == 2
        assert pkg['resources'][3]['position'] == 3
        assert pkg['resources'][3]['name_translated'] == {'en': 'UPDATED', 'fr': 'UPDATED'}
        assert pkg['resources'][4]['position'] == 4
        assert pkg['resources'][5]['position'] == 5

    def test_patching_resource_same_position(self):
        """
        Patching a resource should keep its previous position
        """
        pkg = self.sysadmin_action.package_create(
            name='391112e8-7ade-def0-1234-56789abcd34c',
            resources=[self._new_res(), self._new_res(), self._new_res(),
                       self._new_res(), self._new_res(), self._new_res()],
            **self.pkg_dict)

        assert len(pkg['resources']) == 6
        assert pkg['resources'][0]['position'] == 0
        assert pkg['resources'][1]['position'] == 1
        assert pkg['resources'][2]['position'] == 2
        assert pkg['resources'][3]['position'] == 3
        assert pkg['resources'][4]['position'] == 4
        assert pkg['resources'][5]['position'] == 5

        res_dict = pkg['resources'][3].copy()
        res_dict['name_translated'] = {'en': 'UPDATED', 'fr': 'UPDATED'}

        self.sysadmin_action.resource_patch(**res_dict)

        pkg = self.sysadmin_action.package_show(id=pkg['id'])

        assert len(pkg['resources']) == 6
        assert pkg['resources'][0]['position'] == 0
        assert pkg['resources'][1]['position'] == 1
        assert pkg['resources'][2]['position'] == 2
        assert pkg['resources'][3]['position'] == 3
        assert pkg['resources'][3]['name_translated'] == {'en': 'UPDATED', 'fr': 'UPDATED'}
        assert pkg['resources'][4]['position'] == 4
        assert pkg['resources'][5]['position'] == 5

        # you cannot patch the position via patch actions
        res_dict = pkg['resources'][1].copy()
        res_dict['name_translated'] = {'en': 'UPDATED AGAIN', 'fr': 'UPDATED AGAIN'}
        res_dict['position'] = 99

        self.sysadmin_action.resource_patch(**res_dict)

        pkg = self.sysadmin_action.package_show(id=pkg['id'])

        assert len(pkg['resources']) == 6
        assert pkg['resources'][0]['position'] == 0
        assert pkg['resources'][1]['position'] == 1
        assert pkg['resources'][1]['position'] != 99
        assert pkg['resources'][1]['name_translated'] == {'en': 'UPDATED AGAIN', 'fr': 'UPDATED AGAIN'}
        assert pkg['resources'][2]['position'] == 2
        assert pkg['resources'][3]['position'] == 3
        assert pkg['resources'][3]['name_translated'] == {'en': 'UPDATED', 'fr': 'UPDATED'}
        assert pkg['resources'][4]['position'] == 4
        assert pkg['resources'][5]['position'] == 5

    def test_delete_resource_assigns_positions(self):
        """
        Deleting a Resource from a package should reorder the other
        Resources properly, and set the deleted position to null.
        """
        pkg = self.sysadmin_action.package_create(
            name='44cefde8-7cce-defc-1234-56789abcd34c',
            resources=[self._new_res(), self._new_res(), self._new_res(),
                       self._new_res(), self._new_res(), self._new_res()],
            **self.pkg_dict)

        assert len(pkg['resources']) == 6
        assert pkg['resources'][0]['position'] == 0
        assert pkg['resources'][1]['position'] == 1
        assert pkg['resources'][2]['position'] == 2
        assert pkg['resources'][3]['position'] == 3
        assert pkg['resources'][4]['position'] == 4
        assert pkg['resources'][5]['position'] == 5

        # test single delete resource
        deleted_res_id = pkg['resources'][2]['id']

        self.sysadmin_action.resource_delete(
            id=deleted_res_id)

        pkg = self.sysadmin_action.package_show(id=pkg['id'])

        assert len(pkg['resources']) == 5
        assert pkg['resources'][0]['position'] == 0
        assert pkg['resources'][1]['position'] == 1
        assert pkg['resources'][2]['position'] == 2
        assert pkg['resources'][3]['position'] == 3
        assert pkg['resources'][4]['position'] == 4
        for r in pkg['resources']:
            assert r['id'] != deleted_res_id

        res = model.Resource.get(deleted_res_id)

        assert res.id == deleted_res_id
        assert res.position is None

        # test mass soft delete resources
        old_resource_ids = []
        for r in pkg['resources']:
            old_resource_ids.append(r['id'])

        pkg = self.sysadmin_action.package_patch(
            id=pkg['id'],
            resources=[self._new_res(), self._new_res(), self._new_res(),
                       self._new_res(), self._new_res(), self._new_res()])

        assert len(pkg['resources']) == 6
        assert pkg['resources'][0]['position'] == 0
        assert pkg['resources'][1]['position'] == 1
        assert pkg['resources'][2]['position'] == 2
        assert pkg['resources'][3]['position'] == 3
        assert pkg['resources'][4]['position'] == 4
        assert pkg['resources'][5]['position'] == 5

        pkg = self.sysadmin_action.package_show(id=pkg['id'])

        for r in pkg['resources']:
            assert r['id'] not in old_resource_ids

        for rid in old_resource_ids:
            res = model.Resource.get(rid)
            assert res.state == 'deleted'
            assert res.position is None

        # test mass purge/hard delete resources
        pkg = self.sysadmin_action.package_patch(
            id=pkg['id'],
            resources=[self._new_res(), self._new_res(), self._new_res(),
                       self._new_res(), self._new_res(), self._new_res()])

        assert len(pkg['resources']) == 6
        assert pkg['resources'][0]['position'] == 0
        assert pkg['resources'][1]['position'] == 1
        assert pkg['resources'][2]['position'] == 2
        assert pkg['resources'][3]['position'] == 3
        assert pkg['resources'][4]['position'] == 4
        assert pkg['resources'][5]['position'] == 5

        for rid in old_resource_ids:
            res = model.Resource.get(rid)
            assert res is None

    def test_reorder_resource_positions(self):
        """
        You can reorder Resources via package_resource_reorder action.
        """
        pkg = self.sysadmin_action.package_create(
            name='391112e8-7cce-defc-1234-56789abcd34c',
            resources=[self._new_res(), self._new_res(), self._new_res(),
                       self._new_res(), self._new_res(), self._new_res()],
            **self.pkg_dict)

        assert len(pkg['resources']) == 6
        assert pkg['resources'][0]['position'] == 0
        assert pkg['resources'][1]['position'] == 1
        assert pkg['resources'][2]['position'] == 2
        assert pkg['resources'][3]['position'] == 3
        assert pkg['resources'][4]['position'] == 4
        assert pkg['resources'][5]['position'] == 5

        original_order = [
            pkg['resources'][0]['id'],
            pkg['resources'][1]['id'],
            pkg['resources'][2]['id'],
            pkg['resources'][3]['id'],
            pkg['resources'][4]['id'],
            pkg['resources'][5]['id'],
        ]

        new_order = [
            pkg['resources'][4]['id'],
            pkg['resources'][5]['id'],
            pkg['resources'][0]['id'],
            pkg['resources'][2]['id'],
            pkg['resources'][3]['id'],
            pkg['resources'][1]['id'],
        ]

        self.sysadmin_action.package_resource_reorder(
            id=pkg['id'],
            order=new_order)

        pkg = self.sysadmin_action.package_show(id=pkg['id'])

        assert original_order != new_order
        for i, r in enumerate(pkg['resources']):
            assert r['position'] >= 0
            assert r['id'] != original_order[i]

    def test_unique_positions(self):
        """
        Position values should be unique per dataset.
        """
        pkg = self.sysadmin_action.package_create(
            name='391112e8-7cce-defc-ee66-56789abcd34c',
            resources=[self._new_res(), self._new_res(), self._new_res()],
            **self.pkg_dict)

        assert len(pkg['resources']) == 3

        res3 = model.Resource.get(pkg['resources'][2]['id'])
        res3.position = 1

        with pytest.raises(IntegrityError) as e:
            model.Session.add(res3)
            model.Session.commit()
        model.Session.rollback()
        err = e.value
        assert 'duplicate key value violates unique constraint "con_package_resource_unique_position"' in str(err)

    @pytest.mark.usefixtures("mock_uploads")
    def test_upload_resource_after_reorder(self, mock_uploads):  # noqa: F811
        """
        Having different resource positions in the database
        should still allow for proper Resource uploads when
        updating a resource/package.

        NOTE: this flaky error is based on db object return of resources
              in the package orm object. So we close and open db sessions
              inside of this test to emulate browser request sessions.
              Because of the flakiness, we update every resource w/ upload
              in a new db session.
        """
        pkg = self.sysadmin_action.package_create(
            name='391112e8-1ffd-defc-1234-56789abcd34c',
            resources=[self._new_res(), self._new_res(), self._new_res(),
                       self._new_res(), self._new_res(), self._new_res()],
            **self.pkg_dict)

        assert len(pkg['resources']) == 6
        assert pkg['resources'][0]['position'] == 0
        assert pkg['resources'][1]['position'] == 1
        assert pkg['resources'][2]['position'] == 2
        assert pkg['resources'][3]['position'] == 3
        assert pkg['resources'][4]['position'] == 4
        assert pkg['resources'][5]['position'] == 5

        # upload sample file for all resources
        sample_filepath = get_sample_filepath('example_image_1.png')
        for i, r in enumerate(pkg['resources']):
            fake_file_obj = io.BytesIO()
            with open(sample_filepath, 'rb') as f:
                file_data_r1 = f.read()
                fake_file_obj.write(file_data_r1)
                mock_field_store_r1 = MockFieldStorage(fake_file_obj, 'example_image_1.png')

                fake_stream_r1 = io.BufferedReader(io.BytesIO(file_data_r1))

            with mock.patch('io.open', return_value=fake_stream_r1):
                model.Session.commit()
                model.Session.remove()
                _session = model.Session  # noqa: F841
                r['url'] = '__upload'
                r['url_type'] = 'upload'
                r['format'] = 'PNG'
                r['upload'] = mock_field_store_r1
                self.sysadmin_action.resource_update(**r)

            res = self.sysadmin_action.resource_show(id=r['id'])
            assert res['id'] == r['id']
            assert res['position'] == i
            assert res['url_type'] == 'upload'
            assert res['format'] == 'PNG'
            assert re.match(rf'.*/dataset/{pkg["id"]}/resource/{r["id"]}/download/example_image_1.png$', res['url']) is not None

        original_order = [
            pkg['resources'][0]['id'],
            pkg['resources'][1]['id'],
            pkg['resources'][2]['id'],
            pkg['resources'][3]['id'],
            pkg['resources'][4]['id'],
            pkg['resources'][5]['id'],
        ]

        new_order = [
            pkg['resources'][4]['id'],
            pkg['resources'][5]['id'],
            pkg['resources'][0]['id'],
            pkg['resources'][2]['id'],
            pkg['resources'][3]['id'],
            pkg['resources'][1]['id'],
        ]

        self.sysadmin_action.package_resource_reorder(
            id=pkg['id'],
            order=new_order)

        pkg = self.sysadmin_action.package_show(id=pkg['id'])

        assert original_order != new_order
        for i, r in enumerate(pkg['resources']):
            assert r['position'] >= 0
            assert r['id'] != original_order[i]

        # update sample file upload for all resources
        sample_filepath = get_sample_filepath('example_image_2.png')
        for i, r in enumerate(pkg['resources']):
            fake_file_obj = io.BytesIO()
            with open(sample_filepath, 'rb') as f:
                file_data_r2 = f.read()
                fake_file_obj.write(file_data_r2)
                mock_field_store_r2 = MockFieldStorage(fake_file_obj, 'example_image_2.png')

                fake_stream_r2 = io.BufferedReader(io.BytesIO(file_data_r2))

            with mock.patch('io.open', return_value=fake_stream_r2):
                model.Session.commit()
                model.Session.remove()
                _session = model.Session  # noqa: F841
                r['upload'] = mock_field_store_r2
                self.sysadmin_action.resource_update(**r)

            res = self.sysadmin_action.resource_show(id=r['id'])
            assert res['id'] == r['id']
            assert r['id'] != original_order[i]
            assert res['url_type'] == 'upload'
            assert res['format'] == 'PNG'
            assert re.match(rf'.*/dataset/{pkg["id"]}/resource/{r["id"]}/download/example_image_2.png$', res['url']) is not None

            upload = uploader.get_resource_uploader(res)
            filepath = upload.get_path(res['id'])

            with open(filepath, 'rb') as current_file:
                current_file_data = current_file.read()
                assert current_file_data != file_data_r1
                assert current_file_data == file_data_r2

        # test adding a new file and resource
        sample_filepath = get_sample_filepath('example_image_1.png')
        fake_file_obj = io.BytesIO()
        with open(sample_filepath, 'rb') as f:
            file_data_rnew1 = f.read()
            fake_file_obj.write(file_data_rnew1)
            mock_field_store_rnew1 = MockFieldStorage(fake_file_obj, 'example_image_1.png')

            fake_stream_rnew = io.BufferedReader(io.BytesIO(file_data_rnew1))

        with mock.patch('io.open', return_value=fake_stream_rnew):
            model.Session.commit()
            model.Session.remove()
            _session = model.Session  # noqa: F841
            res = Resource(id='aa111aa1-1ffd-defc-1234-56789abcd34c',
                           package_id=pkg['id'], upload=mock_field_store_rnew1)

        assert res['position'] == 6
        assert re.match(rf'.*/dataset/{pkg["id"]}/resource/{res["id"]}/download/example_image_1.png$', res['url']) is not None

        upload = uploader.get_resource_uploader(res)
        filepath = upload.get_path(res['id'])

        with open(filepath, 'rb') as current_file:
            current_file_data = current_file.read()
            assert current_file_data == file_data_r1
            assert current_file_data == file_data_rnew1
            assert current_file_data != file_data_r2

        # test updating the new file upload
        sample_filepath = get_sample_filepath('example_image_2.png')
        fake_file_obj = io.BytesIO()
        with open(sample_filepath, 'rb') as f:
            file_data_rnew2 = f.read()
            fake_file_obj.write(file_data_rnew2)
            mock_field_store_rnew2 = MockFieldStorage(fake_file_obj, 'example_image_2.png')

            fake_stream_rnew2 = io.BufferedReader(io.BytesIO(file_data_rnew2))

        with mock.patch('io.open', return_value=fake_stream_rnew2):
            res['upload'] = mock_field_store_rnew2
            self.sysadmin_action.resource_update(**res)

        res = self.sysadmin_action.resource_show(id=res['id'])

        assert res['position'] == 6
        assert re.match(rf'.*/dataset/{pkg["id"]}/resource/{res["id"]}/download/example_image_2.png$', res['url']) is not None

        upload = uploader.get_resource_uploader(res)
        filepath = upload.get_path(res['id'])

        with open(filepath, 'rb') as current_file:
            current_file_data = current_file.read()
            assert current_file_data == file_data_r2
            assert current_file_data == file_data_rnew2
            assert current_file_data != file_data_r1
            assert current_file_data != file_data_rnew1
