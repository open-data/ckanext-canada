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
