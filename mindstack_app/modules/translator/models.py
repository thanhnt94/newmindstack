from datetime import datetime
from mindstack_app.core.extensions import db

class TranslationHistory(db.Model):
    __tablename__ = 'translation_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    translated_text = db.Column(db.Text, nullable=False)
    source_lang = db.Column(db.String(10), nullable=True)
    target_lang = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    user = db.relationship('User', backref=db.backref('translation_history', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'original_text': self.original_text,
            'translated_text': self.translated_text,
            'source_lang': self.source_lang,
            'target_lang': self.target_lang,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
