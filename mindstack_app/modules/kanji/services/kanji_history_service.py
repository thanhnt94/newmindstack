import logging
from datetime import datetime, timezone
from mindstack_app.core.extensions import db
from ..models import UserKanjiHistory

logger = logging.getLogger(__name__)


class KanjiHistoryService:
    """
    Manages per-user Kanji search history and personal notes.
    """

    @staticmethod
    def record_search(user_id: int, kanji: str) -> UserKanjiHistory:
        """
        Record a Kanji search for a user.
        If the Kanji was already searched, increment search_count and update last_searched_at.
        Otherwise, create a new entry.
        """
        try:
            entry = UserKanjiHistory.query.filter_by(
                user_id=user_id, kanji=kanji
            ).first()

            if entry:
                entry.search_count += 1
                entry.last_searched_at = datetime.now(timezone.utc)
            else:
                entry = UserKanjiHistory(
                    user_id=user_id,
                    kanji=kanji,
                )
                db.session.add(entry)

            db.session.commit()
            return entry
        except Exception as e:
            logger.error(f"Failed to record kanji search: {e}")
            db.session.rollback()
            return None

    @staticmethod
    def get_user_history(user_id: int, limit: int = 50):
        """
        Fetch the user's Kanji search history, ordered by most recent.
        """
        return (
            UserKanjiHistory.query
            .filter_by(user_id=user_id)
            .order_by(UserKanjiHistory.last_searched_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def update_note(user_id: int, kanji: str, note: str) -> UserKanjiHistory:
        """
        Save or update a user's personal note for a specific Kanji.
        Creates a history entry if one doesn't exist yet.
        """
        try:
            entry = UserKanjiHistory.query.filter_by(
                user_id=user_id, kanji=kanji
            ).first()

            if entry:
                entry.note = note
            else:
                entry = UserKanjiHistory(
                    user_id=user_id,
                    kanji=kanji,
                    note=note,
                    search_count=0,  # Note added without a search
                )
                db.session.add(entry)

            db.session.commit()
            return entry
        except Exception as e:
            logger.error(f"Failed to update kanji note: {e}")
            db.session.rollback()
            return None

    @staticmethod
    def get_note(user_id: int, kanji: str):
        """
        Get the user's personal note for a specific Kanji.
        """
        entry = UserKanjiHistory.query.filter_by(
            user_id=user_id, kanji=kanji
        ).first()
        return entry.note if entry else None

    @staticmethod
    def delete_history_entry(user_id: int, kanji: str) -> bool:
        """
        Remove a Kanji from the user's history.
        """
        try:
            entry = UserKanjiHistory.query.filter_by(
                user_id=user_id, kanji=kanji
            ).first()
            if entry:
                db.session.delete(entry)
                db.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete kanji history: {e}")
            db.session.rollback()
            return False
