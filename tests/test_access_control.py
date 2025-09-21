import pytest

from flask_login import login_user, logout_user

from mindstack_app import db
from mindstack_app.models import (
    ContainerContributor,
    LearningContainer,
    LearningItem,
    User,
)
from mindstack_app.modules.learning.flashcard_learning.algorithms import (
    get_filtered_flashcard_sets,
)
from mindstack_app.modules.learning.quiz_learning.algorithms import (
    get_filtered_quiz_sets,
)
from mindstack_app.modules.learning.flashcard_learning.session_manager import (
    FlashcardSessionManager,
)
from mindstack_app.modules.learning.quiz_learning.session_manager import (
    QuizSessionManager,
)


@pytest.fixture
def seeded_data(app):
    with app.app_context():
        free_user = User(username='free_user', email='free@example.com', user_role=User.ROLE_FREE)
        free_user.set_password('password')

        free_user_no_sets = User(username='free_empty', email='free_empty@example.com', user_role=User.ROLE_FREE)
        free_user_no_sets.set_password('password')

        regular_user = User(username='regular_user', email='regular@example.com', user_role=User.ROLE_USER)
        regular_user.set_password('password')

        other_user = User(username='creator_user', email='creator@example.com', user_role=User.ROLE_USER)
        other_user.set_password('password')

        db.session.add_all([free_user, free_user_no_sets, regular_user, other_user])
        db.session.flush()

        own_flashcard = LearningContainer(
            creator_user_id=free_user.user_id,
            container_type='FLASHCARD_SET',
            title='Free Own Flashcards',
            is_public=False,
        )
        other_public_flashcard = LearningContainer(
            creator_user_id=other_user.user_id,
            container_type='FLASHCARD_SET',
            title='Public Flashcards',
            is_public=True,
        )
        contributed_flashcard = LearningContainer(
            creator_user_id=other_user.user_id,
            container_type='FLASHCARD_SET',
            title='Contributed Flashcards',
            is_public=False,
        )

        own_quiz = LearningContainer(
            creator_user_id=free_user.user_id,
            container_type='QUIZ_SET',
            title='Free Own Quiz',
            is_public=False,
        )
        other_public_quiz = LearningContainer(
            creator_user_id=other_user.user_id,
            container_type='QUIZ_SET',
            title='Public Quiz',
            is_public=True,
        )
        contributed_quiz = LearningContainer(
            creator_user_id=other_user.user_id,
            container_type='QUIZ_SET',
            title='Contributed Quiz',
            is_public=False,
        )

        db.session.add_all([
            own_flashcard,
            other_public_flashcard,
            contributed_flashcard,
            own_quiz,
            other_public_quiz,
            contributed_quiz,
        ])
        db.session.flush()

        db.session.add_all([
            ContainerContributor(
                container_id=contributed_flashcard.container_id,
                user_id=free_user.user_id,
                permission_level='editor',
            ),
            ContainerContributor(
                container_id=contributed_flashcard.container_id,
                user_id=regular_user.user_id,
                permission_level='editor',
            ),
            ContainerContributor(
                container_id=contributed_quiz.container_id,
                user_id=free_user.user_id,
                permission_level='editor',
            ),
            ContainerContributor(
                container_id=contributed_quiz.container_id,
                user_id=regular_user.user_id,
                permission_level='editor',
            ),
        ])

        db.session.add_all([
            LearningItem(
                container_id=other_public_flashcard.container_id,
                item_type='FLASHCARD',
                order_in_container=1,
                content={'front': 'Front', 'back': 'Back'},
            ),
            LearningItem(
                container_id=own_flashcard.container_id,
                item_type='FLASHCARD',
                order_in_container=1,
                content={'front': 'Own Front', 'back': 'Own Back'},
            ),
            LearningItem(
                container_id=contributed_flashcard.container_id,
                item_type='FLASHCARD',
                order_in_container=1,
                content={'front': 'Shared Front', 'back': 'Shared Back'},
            ),
            LearningItem(
                container_id=other_public_quiz.container_id,
                item_type='QUIZ_MCQ',
                order_in_container=1,
                content={
                    'question': 'Q1',
                    'options': {'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D'},
                    'correct_answer': 'A',
                },
            ),
            LearningItem(
                container_id=own_quiz.container_id,
                item_type='QUIZ_MCQ',
                order_in_container=1,
                content={
                    'question': 'Q2',
                    'options': {'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D'},
                    'correct_answer': 'A',
                },
            ),
            LearningItem(
                container_id=contributed_quiz.container_id,
                item_type='QUIZ_MCQ',
                order_in_container=1,
                content={
                    'question': 'Q3',
                    'options': {'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D'},
                    'correct_answer': 'A',
                },
            ),
        ])

        db.session.commit()

        yield {
            'free_user_id': free_user.user_id,
            'free_empty_user_id': free_user_no_sets.user_id,
            'regular_user_id': regular_user.user_id,
            'flashcards': {
                'own': own_flashcard.container_id,
                'public_other': other_public_flashcard.container_id,
                'contributed': contributed_flashcard.container_id,
            },
            'quizzes': {
                'own': own_quiz.container_id,
                'public_other': other_public_quiz.container_id,
                'contributed': contributed_quiz.container_id,
            },
        }


def test_free_user_flashcard_filters_only_own(app, seeded_data):
    with app.test_request_context():
        free_user = User.query.get(seeded_data['free_user_id'])
        login_user(free_user)

        pagination = get_filtered_flashcard_sets(
            free_user.user_id,
            search_query='',
            search_field='all',
            current_filter='all',
            page=1,
            per_page=10,
        )

        returned_ids = {item.container_id for item in pagination.items}
        assert seeded_data['flashcards']['own'] in returned_ids
        assert seeded_data['flashcards']['public_other'] not in returned_ids
        assert seeded_data['flashcards']['contributed'] not in returned_ids

        logout_user()


def test_regular_user_sees_public_flashcard_sets(app, seeded_data):
    with app.test_request_context():
        regular_user = User.query.get(seeded_data['regular_user_id'])
        login_user(regular_user)

        pagination = get_filtered_flashcard_sets(
            regular_user.user_id,
            search_query='',
            search_field='all',
            current_filter='all',
            page=1,
            per_page=10,
        )

        returned_ids = {item.container_id for item in pagination.items}
        assert seeded_data['flashcards']['public_other'] in returned_ids

        logout_user()


def test_free_user_quiz_filters_only_own(app, seeded_data):
    with app.test_request_context():
        free_user = User.query.get(seeded_data['free_user_id'])
        login_user(free_user)

        pagination = get_filtered_quiz_sets(
            free_user.user_id,
            search_query='',
            search_field='all',
            current_filter='all',
            page=1,
            per_page=10,
        )

        returned_ids = {item.container_id for item in pagination.items}
        assert seeded_data['quizzes']['own'] in returned_ids
        assert seeded_data['quizzes']['public_other'] not in returned_ids
        assert seeded_data['quizzes']['contributed'] not in returned_ids

        logout_user()


def test_session_managers_respect_access_controls(app, seeded_data):
    other_flashcard_id = seeded_data['flashcards']['public_other']
    other_quiz_id = seeded_data['quizzes']['public_other']

    with app.test_request_context():
        free_user = User.query.get(seeded_data['free_user_id'])
        login_user(free_user)

        assert not FlashcardSessionManager.start_new_flashcard_session(
            [other_flashcard_id], 'new_only'
        )
        assert not QuizSessionManager.start_new_quiz_session(
            [other_quiz_id], 'new_only', batch_size=5
        )

        logout_user()

    with app.test_request_context():
        empty_user = User.query.get(seeded_data['free_empty_user_id'])
        login_user(empty_user)

        assert not FlashcardSessionManager.start_new_flashcard_session('all', 'new_only')
        assert not QuizSessionManager.start_new_quiz_session('all', 'new_only', batch_size=5)

        logout_user()
