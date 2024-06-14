from ckan.tests.helpers import reset_db
from ckan.lib.search import clear_all
from ckanext.validation.model import (
    create_tables as validation_create_tables,
    tables_exist as validation_tables_exist
)
from ckanext.security.model import db_setup as security_db_setup
from ckan.cli.db import pending_migrations

class CanadaTestBase(object):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        reset_db()
        clear_all()
        if not validation_tables_exist():
            validation_create_tables()
        security_db_setup()
        pending_migrations(True)
