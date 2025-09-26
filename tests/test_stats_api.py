import pytest
from datetime import datetime, timedelta

from mindstack_app import db
from mindstack_app.models import (
    User,
    LearningContainer,
    LearningItem,
    FlashcardProgress,
    QuizProgress,
    CourseProgress,
    ScoreLog,
)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def stats_data(app):
    with app.app_context():
        user = User(username='stats_user', email='stats@example.com', user_role=User.ROLE_USER)
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()

        flashcard_container = LearningContainer(
            creator_user_id=user.user_id,
            container_type='FLASHCARD_SET',
            title='Flashcard Set',
            is_public=False,
        )
        quiz_container = LearningContainer(
            creator_user_id=user.user_id,
            container_type='QUIZ_SET',
            title='Quiz Set',
            is_public=False,
        )
        course_container = LearningContainer(
            creator_user_id=user.user_id,
            container_type='COURSE',
            title='Course Set',
            is_public=False,
        )

        db.session.add_all([flashcard_container, quiz_container, course_container])
        db.session.flush()

        now = datetime.utcnow()
        flashcard_items = []
        for index in range(4):
            flashcard_items.append(
                LearningItem(
                    container_id=flashcard_container.container_id,
                    item_type='FLASHCARD',
                    order_in_container=index,
                    content={'front': f'Card {index + 1}', 'back': f'Back {index + 1}'},
                )
            )
        quiz_items = []
        for index in range(3):
            quiz_items.append(
                LearningItem(
                    container_id=quiz_container.container_id,
                    item_type='QUIZ_MCQ',
                    order_in_container=index,
                    content={
                        'question': f'Question {index + 1}',
                        'options': {'A': 'Opt A', 'B': 'Opt B', 'C': 'Opt C', 'D': 'Opt D'},
                        'correct_answer': 'A',
                    },
                )
            )
        course_items = []
        for index in range(3):
            course_items.append(
                LearningItem(
                    container_id=course_container.container_id,
                    item_type='LESSON',
                    order_in_container=index,
                    content={'title': f'Lesson {index + 1}'},
                )
            )

        db.session.add_all(flashcard_items + quiz_items + course_items)
        db.session.flush()

        flashcard_progress = [
            FlashcardProgress(
                user_id=user.user_id,
                item_id=flashcard_items[0].item_id,
                status='mastered',
                times_correct=5,
                last_reviewed=now - timedelta(days=1),
                due_time=now - timedelta(hours=2),
                review_history=[
                    {'timestamp': (now - timedelta(days=5)).isoformat(), 'type': 'preview'},
                    {'timestamp': (now - timedelta(days=4)).isoformat(), 'user_answer_quality': 5},
                ],
            ),
            FlashcardProgress(
                user_id=user.user_id,
                item_id=flashcard_items[1].item_id,
                status='mastered',
                times_correct=3,
                last_reviewed=now - timedelta(days=2),
                due_time=now - timedelta(hours=5),
                review_history=[
                    {'timestamp': (now - timedelta(days=3)).isoformat(), 'type': 'preview'},
                    {'timestamp': (now - timedelta(days=2)).isoformat(), 'user_answer_quality': 3},
                ],
            ),
            FlashcardProgress(
                user_id=user.user_id,
                item_id=flashcard_items[2].item_id,
                status='learning',
                times_correct=1,
                times_incorrect=2,
                due_time=now - timedelta(hours=1),
                review_history=[
                    {'timestamp': (now - timedelta(days=1)).isoformat(), 'user_answer_quality': 2},
                ],
            ),
            FlashcardProgress(
                user_id=user.user_id,
                item_id=flashcard_items[3].item_id,
                status='new',
                times_correct=0,
                due_time=now + timedelta(days=1),
                review_history=[],
            ),
        ]

        quiz_progress = [
            QuizProgress(
                user_id=user.user_id,
                item_id=quiz_items[0].item_id,
                status='mastered',
                times_correct=4,
                last_reviewed=now - timedelta(days=1),
                review_history=[
                    {'timestamp': (now - timedelta(days=4)).isoformat(), 'is_correct': True, 'score_change': 25},
                    {'timestamp': (now - timedelta(days=1)).isoformat(), 'is_correct': True, 'score_change': 20},
                ],
            ),
            QuizProgress(
                user_id=user.user_id,
                item_id=quiz_items[1].item_id,
                status='learning',
                times_correct=1,
                times_incorrect=3,
                last_reviewed=now - timedelta(days=3),
                review_history=[
                    {'timestamp': (now - timedelta(days=2)).isoformat(), 'is_correct': False, 'score_change': -5},
                ],
            ),
            QuizProgress(
                user_id=user.user_id,
                item_id=quiz_items[2].item_id,
                status='hard',
                times_correct=0,
                times_incorrect=4,
                review_history=[],
            ),
        ]

        course_progress = [
            CourseProgress(
                user_id=user.user_id,
                item_id=course_items[0].item_id,
                completion_percentage=100,
                last_updated=now - timedelta(days=1),
            ),
            CourseProgress(
                user_id=user.user_id,
                item_id=course_items[1].item_id,
                completion_percentage=55,
                last_updated=now - timedelta(hours=5),
            ),
            CourseProgress(
                user_id=user.user_id,
                item_id=course_items[2].item_id,
                completion_percentage=0,
                last_updated=now - timedelta(days=2),
            ),
        ]

        score_logs = [
            ScoreLog(
                user_id=user.user_id,
                item_id=flashcard_items[0].item_id,
                score_change=15,
                item_type='FLASHCARD',
                timestamp=now - timedelta(days=4),
            ),
            ScoreLog(
                user_id=user.user_id,
                item_id=flashcard_items[1].item_id,
                score_change=10,
                item_type='FLASHCARD',
                timestamp=now - timedelta(days=2),
            ),
            ScoreLog(
                user_id=user.user_id,
                item_id=quiz_items[0].item_id,
                score_change=25,
                item_type='QUIZ_MCQ',
                timestamp=now - timedelta(days=4),
            ),
            ScoreLog(
                user_id=user.user_id,
                item_id=quiz_items[1].item_id,
                score_change=-5,
                item_type='QUIZ_MCQ',
                timestamp=now - timedelta(days=2),
            ),
        ]

        db.session.add_all(flashcard_progress + quiz_progress + course_progress + score_logs)
        db.session.commit()

        yield {
            'user_id': user.user_id,
            'flashcard_container': flashcard_container.container_id,
            'quiz_container': quiz_container.container_id,
            'course_container': course_container.container_id,
        }


def login(client, user_id):
    with client.session_transaction() as session:
        session['_user_id'] = str(user_id)
        session['_fresh'] = True


def test_flashcard_items_pagination(client, stats_data):
    login(client, stats_data['user_id'])

    url = f"/stats/api/flashcard-items?container_id={stats_data['flashcard_container']}&status=mastered&per_page=1&page=1"
    response = client.get(url)
    payload = response.get_json()

    assert response.status_code == 200
    assert payload['success'] is True
    assert payload['data']['total'] == 2
    assert len(payload['data']['records']) == 1
    first_item = payload['data']['records'][0]['item_id']

    response_page_2 = client.get(
        f"/stats/api/flashcard-items?container_id={stats_data['flashcard_container']}&status=mastered&per_page=1&page=2"
    )
    payload_page_2 = response_page_2.get_json()
    assert payload_page_2['data']['records'][0]['item_id'] != first_item

    needs_review = client.get(
        f"/stats/api/flashcard-items?container_id={stats_data['flashcard_container']}&status=needs_review"
    ).get_json()
    assert needs_review['data']['total'] == 3
    statuses = {record['status'] for record in needs_review['data']['records']}
    assert 'learning' in statuses


def test_flashcard_metrics_items_summary(client, stats_data):
    login(client, stats_data['user_id'])
    response = client.get(
        f"/stats/api/flashcard-set-metrics?container_id={stats_data['flashcard_container']}&status=mastered&per_page=1&page=1"
    )
    data = response.get_json()['data']
    key = str(stats_data['flashcard_container'])
    assert data[key]['items']['total'] == 2
    assert len(data[key]['items']['records']) == 1


def test_quiz_items_filters(client, stats_data):
    login(client, stats_data['user_id'])
    response = client.get(
        f"/stats/api/quiz-items?container_id={stats_data['quiz_container']}&status=needs_review"
    )
    data = response.get_json()['data']
    assert data['total'] == 2
    statuses = {record['status'] for record in data['records']}
    assert statuses == {'learning', 'hard'}


def test_course_items_status_filter(client, stats_data):
    login(client, stats_data['user_id'])
    completed = client.get(
        f"/stats/api/course-items?container_id={stats_data['course_container']}&status=completed"
    ).get_json()['data']
    assert completed['total'] == 1
    assert completed['records'][0]['status'] == 'completed'

    in_progress = client.get(
        f"/stats/api/course-items?container_id={stats_data['course_container']}&status=in_progress"
    ).get_json()['data']
    assert in_progress['total'] == 1
    assert in_progress['records'][0]['status'] == 'in_progress'


def test_statistics_modal_markup(client, stats_data):
    login(client, stats_data['user_id'])
    response = client.get('/stats/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="stats-modal"' in html
    assert 'data-type="flashcard"' in html
    assert 'data-category="mastered"' in html


def test_flashcard_activity_endpoint(client, stats_data):
    login(client, stats_data['user_id'])
    response = client.get(
        f"/stats/api/flashcard-activity?container_id={stats_data['flashcard_container']}&timeframe=30d"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload['success'] is True
    series = payload['data']['series']
    assert series, "Expected non-empty activity series"
    first_entry = series[0]
    assert {'date', 'new_count', 'review_count', 'score'} <= set(first_entry.keys())
    assert any(point['new_count'] > 0 for point in series)


def test_quiz_activity_endpoint(client, stats_data):
    login(client, stats_data['user_id'])
    response = client.get(
        f"/stats/api/quiz-activity?container_id={stats_data['quiz_container']}&timeframe=30d"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload['success'] is True
    series = payload['data']['series']
    assert series, "Expected non-empty quiz activity series"
    assert any(point['review_count'] > 0 for point in series)


def test_course_activity_endpoint(client, stats_data):
    login(client, stats_data['user_id'])
    response = client.get(
        f"/stats/api/course-activity?container_id={stats_data['course_container']}&timeframe=30d"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload['success'] is True
    series = payload['data']['series']
    assert series, "Expected course activity series response"
    first_entry = series[0]
    assert {'date', 'new_count', 'review_count', 'score'} <= set(first_entry.keys())
