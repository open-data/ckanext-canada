import pytest
from ckan.lib import uploader

@pytest.fixture
def mock_uploads(ckan_config, monkeypatch, tmp_path):
    monkeypatch.setitem(ckan_config, "ckan.storage_path", str(tmp_path))
    monkeypatch.setattr(uploader, "_storage_path", str(tmp_path))
