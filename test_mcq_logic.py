
import os
import sys

# Mocking Flask app context if needed
from flask import Flask
app = Flask(__name__)
# Mock configuration to avoid full init
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///c:/Code/MindStack/database/mindstack_new.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from mindstack_app.models import db
db.init_app(app)

with app.app_context():
    from mindstack_app.modules.vocabulary.mcq.services.mcq_service import MCQService
    
    container_id = 3
    user_id = 1
    config = {'mode': 'all_review', 'count': 1}
    
    questions = MCQService.generate_session_questions(container_id, config, user_id)
    
    if questions:
        q = questions[0]
        print(f"Question Key: {q.get('question_key')}")
        print(f"Answer Key: {q.get('answer_key')}")
        print(f"Question: {q.get('question')}")
        print(f"Correct Answer: {q.get('correct_answer')}")
        print(f"Choices Sample: {q.get('choices')[0] if q.get('choices') else 'None'}")
    else:
        print("No questions generated")
