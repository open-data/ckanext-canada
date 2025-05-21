from ckan.tests.helpers import reset_db
from ckan.lib.search import clear_all
from ckanext.validation.model import (
    create_tables as validation_create_tables,
    tables_exist as validation_tables_exist
)
from ckanext.security.model import db_setup as security_db_setup
from ckanext.canada.triggers import update_triggers
from ckanext.recombinant.cli import _create_triggers
from ckan.cli.db import _run_migrations


def mock_is_registry_domain() -> bool:
    return True


class CanadaTestBase(object):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        # FIXME: DB head for migartions in our test environment setup.
        #        HEAD of CKAN db Docker image is always ahead??
        _run_migrations('canada_public')
        reset_db()
        clear_all()
        if not validation_tables_exist():
            validation_create_tables()
        security_db_setup()
        _run_migrations('activity')
        update_triggers()
        _create_triggers(dataset_types=[], all_types=True)
        _run_migrations('canada_public')
