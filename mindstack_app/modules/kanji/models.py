from datetime import datetime, timezone
from mindstack_app.core.extensions import db


class UserKanjiHistory(db.Model):
    """
    Tracks per-user Kanji search history, personal notes, and statistics.
    One row per (user, kanji) pair — upserted on each search.
    """
    __tablename__ = 'user_kanji_history'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'kanji', name='uq_user_kanji'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    kanji = db.Column(db.String(1), nullable=False)
    note = db.Column(db.Text, nullable=True)
    search_count = db.Column(db.Integer, default=1, nullable=False)
    first_searched_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_searched_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                 onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    user = db.relationship('User', backref=db.backref('kanji_history', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'kanji': self.kanji,
            'note': self.note,
            'search_count': self.search_count,
            'first_searched_at': self.first_searched_at.isoformat() + 'Z' if self.first_searched_at else None,
            'last_searched_at': self.last_searched_at.isoformat() + 'Z' if self.last_searched_at else None,
        }
