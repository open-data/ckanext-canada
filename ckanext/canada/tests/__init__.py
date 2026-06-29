from ckan import model
from ckan.plugins.toolkit import config


def get_test_domains():
    # domain_map = config.get('ckanext.language_domains.domain_map')
    return {
        'registry': {
            'en': 'registry.open.local',
            'fr': 'registry.open.local',
        },
        'portal': {
            'en': 'open.local',
            'fr': 'ouvert.local',
        },
    }


def mock_is_registry_domain() -> bool:
    return True


def mock_is_portal_domain() -> bool:
    return False


class CanadaTestBase(object):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        return

    @classmethod
    def teardown_method(self, method):
        """Method is called at class level after EACH test methods of the class are called.
        Remove any state specific to the execution of the given class methods.
        """
        model.Session.rollback()
        return

    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        return

    @classmethod
    def teardown_class(self):
        """Method is called at class level after ALL test methods of the class are called.
        Remove any state specific to the execution of the given class.
        """
        model.Session.rollback()
        return
