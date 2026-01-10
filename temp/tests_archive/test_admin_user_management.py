import pytest

from mindstack_app import db
from mindstack_app.models import User


@pytest.fixture
def client(app):
    return app.test_client()


def login_as_admin(client):
    return client.post(
        '/auth/login',
        data={'username': 'admin', 'password': 'admin'},
        follow_redirects=True,
    )


def test_admin_can_update_user_details(app, client):
    with app.app_context():
        member = User(username='member', email='member@example.com', user_role=User.ROLE_FREE)
        member.set_password('password')
        db.session.add(member)
        db.session.commit()
        member_id = member.user_id

    login_as_admin(client)

    response = client.post(
        f'/admin/users/edit/{member_id}',
        data={
            'username': 'member_updated',
            'email': 'updated@example.com',
            'user_role': User.ROLE_ADMIN,
            'password': '',
            'password2': '',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert 'Thông tin người dùng đã được cập nhật!' in response.get_data(as_text=True)

    with app.app_context():
        updated_member = User.query.get(member_id)
        assert updated_member.username == 'member_updated'
        assert updated_member.email == 'updated@example.com'
        assert updated_member.user_role == User.ROLE_ADMIN


def test_duplicate_email_shows_validation_error(app, client):
    with app.app_context():
        existing = User(username='existing', email='existing@example.com', user_role=User.ROLE_USER)
        existing.set_password('password')
        target = User(username='target', email='target@example.com', user_role=User.ROLE_FREE)
        target.set_password('password')
        db.session.add_all([existing, target])
        db.session.commit()
        target_id = target.user_id

    login_as_admin(client)

    response = client.post(
        f'/admin/users/edit/{target_id}',
        data={
            'username': 'target',
            'email': 'existing@example.com',
            'user_role': User.ROLE_FREE,
            'password': '',
            'password2': '',
        },
        follow_redirects=True,
    )

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Email này đã được sử dụng.' in body

    with app.app_context():
        unchanged_target = User.query.get(target_id)
        assert unchanged_target.email == 'target@example.com'
