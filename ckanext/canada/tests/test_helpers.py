from ckanext.canada.tests import CanadaTestBase

from ckan.plugins.toolkit import h


class TestCanadaLogic(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestCanadaLogic, self).setup_class()

    def test_obfuscate_to_code_points(self):
        """
        Obfuscating emails should return code point strings.
        """
        email = 'example@example.com'
        expected_result = '&#101;&#120;&#097;&#109;&#112;&#108;&#101;&#064;&#101;&#120;&#097;&#109;&#112;&#108;&#101;&#046;&#099;&#111;&#109;'

        assert h.obfuscate_to_code_points(email) == expected_result
