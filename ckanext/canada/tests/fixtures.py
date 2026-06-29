import pytest
import re
from ckan.lib import uploader


@pytest.fixture
def mock_uploads(ckan_config, monkeypatch, tmp_path):
    def mock_get_storage_path():
        return str(tmp_path)
    monkeypatch.setitem(ckan_config, "ckan.storage_path", str(tmp_path))
    monkeypatch.setattr(uploader, "get_storage_path", mock_get_storage_path)


@pytest.fixture
def strip_lang_prefix_app(app):
    original_wsgi = app.app

    def _wsgi(environ, start_response):
        path = environ.get("PATH_INFO", "")
        environ["PATH_INFO"] = re.sub(r'^/[en|fr]/', '', path) + '/'
        return original_wsgi(environ, start_response)

    app.app = _wsgi
    return app
