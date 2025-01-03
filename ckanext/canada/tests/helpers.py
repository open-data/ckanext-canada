import os
from cgi import FieldStorage


def get_sample_filepath(filename):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "samples", filename))


class MockFieldStorage(FieldStorage):
    def __init__(self, fp, filename):
        self.file = fp
        self.filename = filename
        self.name = 'upload'
        self.list = None

    def __bool__(self):
        if self.file:
            return True
        return False


class MockFlashMessages(object):

    __flashes = []

    def mock_flash(self, message: str, category: str = "message") -> None:
        self.__flashes.append((category, message))

    def mock_get_flashed_messages(self, with_categories: bool = False, category_filter: set = ()):
        flashes = self.__flashes
        if category_filter:
            flashes = list(filter(lambda f: f[0] in category_filter, flashes))
        if not with_categories:
            return [x[1] for x in flashes]
        self.__flashes = []
        return flashes
