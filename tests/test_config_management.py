import os

import pytest
from flask import current_app

from mindstack_app import db
from mindstack_app.models import SystemSetting
from mindstack_app.services.config_service import ConfigService
import mindstack_app.modules.admin.routes as admin_routes


@pytest.fixture
def client(app):
    return app.test_client()


def login_as_admin(client):
    return client.post(
        '/auth/login',
        data={'username': 'admin', 'password': 'admin'},
        follow_redirects=True,
    )


def test_config_service_loads_and_applies_settings(monkeypatch, app):
    class DummyQuery:
        @staticmethod
        def all():
            return [
                SystemSetting(key="FEATURE_ENABLED", value="true", data_type="bool"),
                SystemSetting(key="REQUEST_LIMIT", value="15", data_type="int"),
                SystemSetting(key="STORAGE_PATH", value="./runtime", data_type="path"),
                SystemSetting(key="SECRET_KEY", value="should_ignore", data_type="string"),
            ]

    monkeypatch.setattr(SystemSetting, "query", DummyQuery)

    with app.app_context():
        original_secret = current_app.config.get("SECRET_KEY")
        service = ConfigService(app, ttl_seconds=0)
        service.load_settings(force=True)

        assert current_app.config["FEATURE_ENABLED"] is True
        assert current_app.config["REQUEST_LIMIT"] == 15
        assert os.path.isabs(current_app.config["STORAGE_PATH"])
        assert current_app.config.get("SECRET_KEY") == original_secret


def test_update_setting_applies_to_current_app_config(app, client):
    with app.app_context():
        setting = SystemSetting(key="MAX_ITEMS", value=5, data_type="int")
        db.session.add(setting)
        db.session.commit()
        setting_id = setting.setting_id

    login_as_admin(client)
    response = client.post(
        f"/admin/settings/{setting_id}/update",
        data={"data_type": "int", "description": "", "value": "25"},
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        assert current_app.config["MAX_ITEMS"] == 25


def test_invalid_path_shows_error_message(app, client, monkeypatch):
    login_as_admin(client)

    def raising_makedirs(path, exist_ok=False):  # pragma: no cover - behavior verified via response
        raise OSError("permission denied")

    monkeypatch.setattr(admin_routes.os, "makedirs", raising_makedirs)

    response = client.post(
        "/admin/settings/create",
        data={"key": "DATA_PATH", "data_type": "path", "value": "/root/protected"},
        follow_redirects=True,
    )

    body = response.get_data(as_text=True)
    assert "Không thể tạo hoặc truy cập thư mục" in body
    assert response.status_code == 200
