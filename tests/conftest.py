import os
import sys

import pytest
import types

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if "duckduckgo_search" not in sys.modules:
    duckduckgo_search = types.ModuleType("duckduckgo_search")

    class _StubDuckDuckGoSearchException(Exception):
        pass

    class _StubDDGS:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def images(self, *_args, **_kwargs):
            return []

    duckduckgo_search.DDGS = _StubDDGS
    exceptions_module = types.ModuleType("duckduckgo_search.exceptions")
    exceptions_module.DuckDuckGoSearchException = _StubDuckDuckGoSearchException
    sys.modules["duckduckgo_search"] = duckduckgo_search
    sys.modules["duckduckgo_search.exceptions"] = exceptions_module

from mindstack_app import create_app, db
from mindstack_app.config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False}
    }
    WTF_CSRF_ENABLED = False


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()
