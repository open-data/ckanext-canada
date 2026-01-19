# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN

from ckanext.canada.tests.factories import (
    CanadaResource as Resource,
    CanadaOrganization as Organization,
    CanadaUser as User,
    CanadaSysadminWithToken as Sysadmin
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

        sysadmin = Sysadmin(name='test_metadata_dates_sysadmin')
        editor = User(name='test_metadata_dates_editor')
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
        a metadata_updated value, but not a metadata_created one
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

        assert pkg['metadata_created'] != self.update_date
        assert pkg['metadata_modified'] == self.update_date
        assert pkg['resources'][0]['created'] == self.update_date
        assert pkg['resources'][0]['last_modified'] == self.update_date
        assert pkg['resources'][0]['metadata_modified'] == self.update_date

    def test_package_patch_metadata_fields(self):
        """
        When patching packages and resources, sysadmins should be
        able to provide a metadata_updated value, but not
        a metadata_created one
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

        assert pkg['metadata_created'] != self.update_date
        assert pkg['metadata_modified'] == self.update_date

        res = self.sysadmin_action.resource_patch(
            id=pkg['resources'][0]['id'],
            created=self.update_date,
            last_modified=self.update_date,
            metadata_modified=self.update_date)

        assert res['created'] == self.update_date
        assert res['last_modified'] == self.update_date
        assert res['metadata_modified'] == self.update_date
