import os
import nose

skip_methods = {
}

# More tests that fail due authorization changes from publisher profile.
publisher_profile = {
}


class DataGCCANosePlugin(nose.plugins.Plugin):
    name = 'DataGCCANosePlugin'

    def options(self, parser, env=os.environ):
        super(DataGCCANosePlugin, self).options(parser, env=env)

    def configure(self, options, conf):
        super(DataGCCANosePlugin, self).configure(options, conf)
        self.enabled = True
        self.skipped_tests = []

    def wantMethod(self, method):
        # Skip any methods from skip_methods.
        for d in skip_methods, publisher_profile:
            for test_class in d.keys():
                if test_class in str(getattr(method, 'im_class', None)):
                    if method.__name__ in d[test_class]:
                        self.skipped_tests.append(
                                test_class + '.' + method.__name__)
                        return False
        return None

    # Useful for printing out failing tests for pasting into the skip lists
    # above.
    #failing_tests = {}

    #def add_failing_test(self, test):
    #    test_method = str(test.test).split('.')[-1]
    #    test_class = '.'.join(str(test.test).split('.')[:-1])
    #    if not test_class in self.failing_tests:
    #        self.failing_tests[test_class] = []
    #    self.failing_tests[test_class].append(test_method)

    #def addError(self, test, err):
    #    self.add_failing_test(test)

    #def addFailure(self, test, err):
    #    self.add_failing_test(test)

    def finalize(self, result):
        import pprint
        print "DataGCCANosePlugin skipped {} tests:".format(
                len(self.skipped_tests))
        pprint.pprint(self.skipped_tests)
