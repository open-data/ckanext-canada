from ckan.tests.helpers import FunctionalTestBase
from ckanext.validation.model import (
    create_tables as validation_create_tables,
    tables_exist as validation_tables_exist
)

class CanadaTestBase(FunctionalTestBase):
    def setup(self):
        if not validation_tables_exist():
            validation_create_tables()
        super(CanadaTestBase, self).setup()
