"""Course and Lesson models."""
from __future__ import annotations
from .learning import LearningContainer, LearningItem

class Course(LearningContainer):
    """Specialized LearningContainer for Courses."""
    __mapper_args__ = {
        'polymorphic_identity': 'COURSE'
    }

    def __repr__(self):
        return f"<Course {self.container_id}: {self.title}>"

class Lesson(LearningItem):
    """Specialized LearningItem for Lessons."""
    __mapper_args__ = {
        'polymorphic_identity': 'LESSON'
    }

    @property
    def title(self) -> str:
        """Helper to get title from JSON content."""
        return (self.content or {}).get('title', 'Untitled Lesson')

    def __repr__(self):
        return f"<Lesson {self.item_id}: {self.title}>"
