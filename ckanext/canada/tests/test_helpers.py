from ckanext.canada.tests import CanadaTestBase

from ckan.plugins.toolkit import h


class TestCanadaLogic(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestCanadaLogic, self).setup_class()

    def test_obfuscate_to_code_points(self):
        """
        Obfuscating emails should return code point strings.
        """
        email = 'example@example.com'
        expected_result = '&#101;&#120;&#097;&#109;&#112;&#108;&#101;&#064;&#101;&#120;&#097;&#109;&#112;&#108;&#101;&#046;&#099;&#111;&#109;'

        assert h.obfuscate_to_code_points(email) == expected_result
