import os
import pytest
from io import StringIO
from ckan.lib import uploader
from pyfakefs import fake_filesystem

real_open = open
real_isfile = os.path.isfile
MOCK_IP_ADDRESS = u'174.116.80.148'
MOCK_IP_LIST_FILE = u'test_ip_list'
_fs = fake_filesystem.FakeFilesystem()
_mock_file_open = fake_filesystem.FakeFileOpen(_fs)


@pytest.fixture
def mock_uploads(ckan_config, monkeypatch, tmp_path):
    monkeypatch.setitem(ckan_config, "ckan.storage_path", str(tmp_path))
    monkeypatch.setattr(uploader, "_storage_path", str(tmp_path))


def _mock_open(*args, **kwargs):
    try:
        return real_open(*args, **kwargs)
    except (OSError, IOError):
        return _mock_file_open(*args, **kwargs)


def mock_isfile(filename):
    if MOCK_IP_LIST_FILE in filename:
        return True
    return real_isfile(filename)


def mock_open_ip_list(*args, **kwargs):
    if args and MOCK_IP_LIST_FILE in args[0]:
        return StringIO(MOCK_IP_ADDRESS)
    return _mock_open(*args, **kwargs)
