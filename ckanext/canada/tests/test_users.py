import pytest
from ckan import model
from sqlalchemy.exc import IntegrityError

from ckanext.canada.tests import CanadaTestBase

from ckanext.canada.tests.factories import CanadaUser as User


class TestCanadaUsers(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestCanadaUsers, self).setup_class()

    def test_unique_emails(self):
        """
        Emails should be unique for active users.
        """
        User(email="example@example.com")

        bad_emails = [
            'example@example.com',
            'ExAmPlE@example.com',
            'EXAMPLE@EXAMPLE.COM'
        ]

        for bad_email in bad_emails:
            with pytest.raises(IntegrityError) as e:
                User(email=bad_email)
            model.Session.rollback()
            assert 'duplicate key value violates unique constraint "idx_only_one_active_email_no_case"' in str(e)
