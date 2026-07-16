import pytest
from ckan.lib import uploader
from ckan.tests.pytest_ckan.fixtures import with_plugins


@pytest.fixture
def mock_uploads(ckan_config, monkeypatch, tmp_path):
    def mock_get_storage_path():
        return str(tmp_path)
    monkeypatch.setitem(ckan_config, "ckan.storage_path", str(tmp_path))
    monkeypatch.setattr(uploader, "get_storage_path", mock_get_storage_path)


@pytest.fixture
def use_xloader():
    with_plugins('xloader')
