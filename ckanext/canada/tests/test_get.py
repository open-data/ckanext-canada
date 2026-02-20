# -*- coding: UTF-8 -*-
import pytest

from ckan.tests.factories import Sysadmin
import ckan.tests.helpers as helpers
from ckanext.canada.tests.factories import CanadaUser as User


@pytest.mark.usefixtures("clean_db")
class TestCanadaUserList(object):

    def test_user_list_filtered_by_case_insensitive_email(self):
        sysadmin = Sysadmin()

        user_a = User(email="MixedCaseEmail@example.com")
        user_b = User(email="ALLCAPSEMAIL@example.com")

        # Email with mixed case and whitespace
        got_users = helpers.call_action(
            "user_list",
            context={"user": sysadmin["name"]},
            email="   mixedcaseemail@example.com   ",
            all_fields=False,
        )
        assert len(got_users) == 1
        assert got_users[0] == user_a["name"]

        # Email with all caps
        got_users = helpers.call_action(
            "user_list",
            context={"user": sysadmin["name"]},
            email="allcapsEMAIL@EXAMPLE.com",
            all_fields=False,
        )
        assert len(got_users) == 1
        assert got_users[0] == user_b["name"]
