"""Quiz database models."""

from __future__ import annotations
from mindstack_app.core.extensions import db
from mindstack_app.modules.learning.models import LearningContainer, LearningItem


class QuizSet(LearningContainer):
    """Specialized LearningContainer for Quiz Sets."""
    __mapper_args__ = {
        'polymorphic_identity': 'QUIZ_SET'
    }

    def __repr__(self):
        return f"<QuizSet {self.container_id}: {self.title}>"


class QuizMCQ(LearningItem):
    """Specialized LearningItem for Multiple Choice Questions."""
    __mapper_args__ = {
        'polymorphic_identity': 'QUIZ_MCQ'
    }

    def __repr__(self):
        return f"<QuizMCQ {self.item_id}>"

