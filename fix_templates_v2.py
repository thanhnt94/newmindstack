import os

# MCQ Template
mcq_content = r'''{# MCQ Session Template #}
{% extends "base.html" %}
{% block title %}Trắc nghiệm - {{ container.title }}{% endblock %}
{% block head %}
{{ super() }}
<style>
body { font-family: 'Inter', sans-serif; background: #f8fafc; }
@media (max-width: 1023px) { body > header, body > footer { display: none !important; } body > main { padding: 0 !important; margin: 0 !important; max-width: none !important; } }
.mcq-container { min-height: 100vh; display: flex; flex-direction: column; }
.mcq-header { background: white; padding: 0.75rem 1rem; border-bottom: 1px solid #e2e8f0; display: flex; align-items: center; gap: 0.75rem; }
.mcq-back { width: 36px; height: 36px; border-radius: 0.75rem; background: #f1f5f9; display: flex; align-items: center; justify-content: center; color: #64748b; cursor: pointer; text-decoration: none; }
.mcq-title { font-weight: 700; color: #1e293b; flex: 1; }
.mcq-score { font-weight: 700; color: #6366f1; }
.mcq-content { flex: 1; padding: 1.5rem; max-width: 600px; margin: 0 auto; width: 100%; }
.mcq-prompt { font-size: 1.5rem; font-weight: 700; color: #1e293b; text-align: center; margin-bottom: 2rem; }
.mcq-choices { display: flex; flex-direction: column; gap: 0.75rem; }
.mcq-choice { padding: 1rem 1.25rem; background: white; border: 2px solid #e2e8f0; border-radius: 0.75rem; cursor: pointer; transition: all 0.2s; font-weight: 500; color: #1e293b; }
.mcq-choice:hover { border-color: #6366f1; background: #f5f3ff; }
.mcq-choice.selected { border-color: #6366f1; background: #ede9fe; }
.mcq-choice.correct { border-color: #10b981; background: #d1fae5; color: #059669; }
.mcq-choice.wrong { border-color: #ef4444; background: #fee2e2; color: #dc2626; }
.mcq-next { padding: 1rem; background: white; border-top: 1px solid #e2e8f0; }
.mcq-next-btn { width: 100%; padding: 1rem; background: #6366f1; color: white; border: none; border-radius: 0.75rem; font-weight: 700; cursor: pointer; display: none; }
.mcq-next-btn.show { display: block; }
.mcq-complete { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; }
.mcq-complete-box { background: white; padding: 2rem; border-radius: 1rem; text-align: center; max-width: 300px; }
.mcq-complete-icon { font-size: 4rem; color: #10b981; margin-bottom: 1rem; }
.mcq-complete-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin-bottom: 0.5rem; }
.mcq-complete-stats { color: #64748b; margin-bottom: 1rem; }
.mcq-complete-btn { padding: 0.75rem 1.5rem; background: #6366f1; color: white; border: none; border-radius: 0.5rem; font-weight: 600; cursor: pointer; }
</style>
{% endblock %}
{% block content %}
<div class="mcq-container">
    <div class="mcq-header">
        <a href="{{ url_for('learning.vocabulary.dashboard') }}" class="mcq-back"><i class="fas fa-arrow-left"></i></a>
        <span class="mcq-title">{{ container.title }}</span>
        <span class="mcq-score"><span id="score">0</span>/<span id="total">{{ total_items }}</span></span>
    </div>
    <div class="mcq-content">
        <div class="mcq-prompt" id="prompt">Đang tải...</div>
        <div class="mcq-choices" id="choices"></div>
    </div>
    <div class="mcq-next">
        <button class="mcq-next-btn" id="next-btn">Câu tiếp theo</button>
    </div>
</div>
<div class="mcq-complete" id="complete-modal" style="display: none;">
    <div class="mcq-complete-box">
        <div class="mcq-complete-icon"><i class="fas fa-check-circle"></i></div>
        <div class="mcq-complete-title">Hoàn thành!</div>
        <div class="mcq-complete-stats">Đúng <span id="final-score">0</span>/<span id="final-total">0</span> câu</div>
        <button class="mcq-complete-btn" onclick="location.reload()">Chơi lại</button>
    </div>
</div>
{% endblock %}
{% block scripts %}
{{ super() }}
<script>
(function() {
    var setId = {{ container.container_id }};
    var questions = [];
    var current = 0;
    var score = 0;
    var answered = false;
    var promptEl = document.getElementById('prompt');
    var choicesEl = document.getElementById('choices');
    var nextBtn = document.getElementById('next-btn');
    var scoreEl = document.getElementById('score');
    fetch('/learn/vocabulary/mcq/api/questions/' + setId + '?count=10')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                questions = data.questions;
                document.getElementById('total').textContent = questions.length;
                document.getElementById('final-total').textContent = questions.length;
                showQuestion();
            }
        });
    function showQuestion() {
        if (current >= questions.length) {
            showComplete();
            return;
        }
        answered = false;
        nextBtn.classList.remove('show');
        var q = questions[current];
        promptEl.textContent = q.prompt;
        var html = '';
        q.choices.forEach(function(choice, i) {
            html += '<div class="mcq-choice" data-index="' + i + '" data-answer="' + choice + '">' + choice + '</div>';
        });
        choicesEl.innerHTML = html;
        document.querySelectorAll('.mcq-choice').forEach(function(el) {
            el.onclick = function() {
                if (answered) return;
                checkAnswer(el);
            };
        });
    }
    function checkAnswer(el) {
        answered = true;
        var selected = el.dataset.answer;
        var q = questions[current];
        if (selected === q.correct_answer) {
            el.classList.add('correct');
            score++;
            scoreEl.textContent = score;
        } else {
            el.classList.add('wrong');
            document.querySelectorAll('.mcq-choice').forEach(function(c) {
                if (c.dataset.answer === q.correct_answer) {
                    c.classList.add('correct');
                }
            });
        }
        nextBtn.classList.add('show');
    }
    nextBtn.onclick = function() {
        current++;
        showQuestion();
    };
    function showComplete() {
        document.getElementById('final-score').textContent = score;
        document.getElementById('complete-modal').style.display = 'flex';
    }
})();
</script>
{% endblock %}'''

# Typing Template
typing_content = r'''{# Typing Session Template #}
{% extends "base.html" %}
{% block title %}Gõ đáp án - {{ container.title }}{% endblock %}
{% block head %}
{{ super() }}
<style>
body { font-family: 'Inter', sans-serif; background: #f8fafc; }
@media (max-width: 1023px) { body > header, body > footer { display: none !important; } body > main { padding: 0 !important; margin: 0 !important; max-width: none !important; } }
.typing-container { min-height: 100vh; display: flex; flex-direction: column; }
.typing-header { background: white; padding: 0.75rem 1rem; border-bottom: 1px solid #e2e8f0; display: flex; align-items: center; gap: 0.75rem; }
.typing-back { width: 36px; height: 36px; border-radius: 0.75rem; background: #f1f5f9; display: flex; align-items: center; justify-content: center; color: #64748b; text-decoration: none; }
.typing-title { font-weight: 700; color: #1e293b; flex: 1; }
.typing-score { font-weight: 700; color: #6366f1; }
.typing-content { flex: 1; padding: 1.5rem; max-width: 600px; margin: 0 auto; width: 100%; display: flex; flex-direction: column; justify-content: center; }
.typing-prompt { font-size: 2rem; font-weight: 800; color: #1e293b; text-align: center; margin-bottom: 2rem; }
.typing-input-wrap { position: relative; }
.typing-input { width: 100%; padding: 1rem; font-size: 1.25rem; border: 2px solid #e2e8f0; border-radius: 0.75rem; text-align: center; outline: none; transition: border-color 0.2s; }
.typing-input:focus { border-color: #6366f1; }
.typing-input.correct { border-color: #10b981; background: #d1fae5; }
.typing-input.wrong { border-color: #ef4444; background: #fee2e2; }
.typing-feedback { text-align: center; margin-top: 1rem; min-height: 2rem; }
.typing-correct-answer { color: #10b981; font-weight: 600; }
.typing-wrong-answer { color: #ef4444; font-weight: 600; }
.typing-footer { padding: 1rem; background: white; border-top: 1px solid #e2e8f0; }
.typing-btn { width: 100%; padding: 1rem; background: #6366f1; color: white; border: none; border-radius: 0.75rem; font-weight: 700; cursor: pointer; }
.typing-complete { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; }
.typing-complete-box { background: white; padding: 2rem; border-radius: 1rem; text-align: center; max-width: 300px; }
.typing-complete-icon { font-size: 4rem; color: #10b981; margin-bottom: 1rem; }
.typing-complete-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin-bottom: 0.5rem; }
.typing-complete-stats { color: #64748b; margin-bottom: 1rem; }
.typing-complete-btn { padding: 0.75rem 1.5rem; background: #6366f1; color: white; border: none; border-radius: 0.5rem; font-weight: 600; cursor: pointer; }
</style>
{% endblock %}
{% block content %}
<div class="typing-container">
    <div class="typing-header">
        <a href="{{ url_for('learning.vocabulary.dashboard') }}" class="typing-back"><i class="fas fa-arrow-left"></i></a>
        <span class="typing-title">{{ container.title }}</span>
        <span class="typing-score"><span id="score">0</span>/<span id="total">{{ total_items }}</span></span>
    </div>
    <div class="typing-content">
        <div class="typing-prompt" id="prompt">Đang tải...</div>
        <div class="typing-input-wrap">
            <input type="text" class="typing-input" id="answer-input" placeholder="Gõ đáp án..." autocomplete="off">
        </div>
        <div class="typing-feedback" id="feedback"></div>
    </div>
    <div class="typing-footer">
        <button class="typing-btn" id="submit-btn">Kiểm tra</button>
    </div>
</div>
<div class="typing-complete" id="complete-modal" style="display: none;">
    <div class="typing-complete-box">
        <div class="typing-complete-icon"><i class="fas fa-check-circle"></i></div>
        <div class="typing-complete-title">Hoàn thành!</div>
        <div class="typing-complete-stats">Đúng <span id="final-score">0</span>/<span id="final-total">0</span> câu</div>
        <button class="typing-complete-btn" onclick="location.reload()">Chơi lại</button>
    </div>
</div>
{% endblock %}
{% block scripts %}
{{ super() }}
<script>
(function() {
    var setId = {{ container.container_id }};
    var items = [];
    var current = 0;
    var score = 0;
    var answered = false;
    var promptEl = document.getElementById('prompt');
    var inputEl = document.getElementById('answer-input');
    var feedbackEl = document.getElementById('feedback');
    var submitBtn = document.getElementById('submit-btn');
    var scoreEl = document.getElementById('score');
    fetch('/learn/vocabulary/typing/api/items/' + setId + '?count=10')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                items = data.items;
                document.getElementById('total').textContent = items.length;
                document.getElementById('final-total').textContent = items.length;
                showItem();
            }
        });
    function showItem() {
        if (current >= items.length) {
            showComplete();
            return;
        }
        answered = false;
        inputEl.value = '';
        inputEl.className = 'typing-input';
        inputEl.disabled = false;
        inputEl.focus();
        feedbackEl.innerHTML = '';
        submitBtn.textContent = 'Kiểm tra';
        var item = items[current];
        promptEl.textContent = item.prompt;
    }
    submitBtn.onclick = function() {
        if (!answered) {
            checkAnswer();
        } else {
            current++;
            showItem();
        }
    };
    inputEl.onkeypress = function(e) {
        if (e.key === 'Enter' && !answered) {
            checkAnswer();
        }
    };
    function checkAnswer() {
        var item = items[current];
        var userAnswer = inputEl.value.trim().toLowerCase();
        var correctAnswer = item.answer.trim().toLowerCase();
        answered = true;
        inputEl.disabled = true;
        if (userAnswer === correctAnswer) {
            inputEl.classList.add('correct');
            feedbackEl.innerHTML = '<span class="typing-correct-answer">✓ Chính xác!</span>';
            score++;
            scoreEl.textContent = score;
        } else {
            inputEl.classList.add('wrong');
            feedbackEl.innerHTML = '<span class="typing-wrong-answer">✗ Đáp án: ' + item.answer + '</span>';
        }
        submitBtn.textContent = 'Tiếp theo';
    }
    function showComplete() {
        document.getElementById('final-score').textContent = score;
        document.getElementById('complete-modal').style.display = 'flex';
    }
})();
</script>
{% endblock %}'''

# Matching Template
matching_content = r'''{# Matching Session Template #}
{% extends "base.html" %}
{% block title %}Ghép đôi - {{ container.title }}{% endblock %}
{% block head %}
{{ super() }}
<style>
body { font-family: 'Inter', sans-serif; background: #f8fafc; }
@media (max-width: 1023px) { body > header, body > footer { display: none !important; } body > main { padding: 0 !important; margin: 0 !important; max-width: none !important; } }
.match-container { min-height: 100vh; display: flex; flex-direction: column; }
.match-header { background: white; padding: 0.75rem 1rem; border-bottom: 1px solid #e2e8f0; display: flex; align-items: center; gap: 0.75rem; }
.match-back { width: 36px; height: 36px; border-radius: 0.75rem; background: #f1f5f9; display: flex; align-items: center; justify-content: center; color: #64748b; cursor: pointer; text-decoration: none; }
.match-title { font-weight: 700; color: #1e293b; flex: 1; }
.match-score { font-weight: 700; color: #6366f1; }
.match-game { flex: 1; padding: 1rem; display: flex; gap: 1rem; }
.match-column { flex: 1; display: flex; flex-direction: column; gap: 0.5rem; }
.match-card { padding: 1rem; background: white; border-radius: 0.75rem; border: 2px solid #e2e8f0; cursor: pointer; transition: all 0.2s; text-align: center; font-weight: 500; color: #1e293b; }
.match-card:hover { border-color: #6366f1; background: #f5f3ff; }
.match-card.selected { border-color: #6366f1; background: #ede9fe; box-shadow: 0 0 0 3px rgba(99,102,241,0.2); }
.match-card.matched { border-color: #10b981; background: #d1fae5; color: #059669; pointer-events: none; }
.match-card.wrong { border-color: #ef4444; background: #fee2e2; animation: shake 0.3s; }
@keyframes shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-5px); } 75% { transform: translateX(5px); } }
.match-complete { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 100; }
.match-complete-box { background: white; padding: 2rem; border-radius: 1rem; text-align: center; max-width: 300px; }
.match-complete-icon { font-size: 4rem; color: #10b981; margin-bottom: 1rem; }
.match-complete-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin-bottom: 0.5rem; }
.match-complete-stats { color: #64748b; margin-bottom: 1rem; }
.match-complete-btn { padding: 0.75rem 1.5rem; background: #6366f1; color: white; border: none; border-radius: 0.5rem; font-weight: 600; cursor: pointer; }
</style>
{% endblock %}
{% block content %}
<div class="match-container">
    <div class="match-header">
        <a href="{{ url_for('learning.vocabulary.dashboard') }}" class="match-back"><i class="fas fa-arrow-left"></i></a>
        <span class="match-title">{{ container.title }}</span>
        <span class="match-score"><span id="score">0</span>/{{ game.total }}</span>
    </div>
    <div class="match-game">
        <div class="match-column" id="left-col">
            {% for item in game.left %}
            <div class="match-card" data-side="left" data-item-id="{{ item.item_id }}" data-id="{{ item.id }}">
                {{ item.text }}
            </div>
            {% endfor %}
        </div>
        <div class="match-column" id="right-col">
            {% for item in game.right %}
            <div class="match-card" data-side="right" data-item-id="{{ item.item_id }}" data-id="{{ item.id }}">
                {{ item.text }}
            </div>
            {% endfor %}
        </div>
    </div>
</div>
<div class="match-complete" id="complete-modal" style="display: none;">
    <div class="match-complete-box">
        <div class="match-complete-icon"><i class="fas fa-check-circle"></i></div>
        <div class="match-complete-title">Hoàn thành!</div>
        <div class="match-complete-stats">Bạn đã ghép đúng <span id="final-score">0</span> cặp</div>
        <button class="match-complete-btn" onclick="location.reload()">Chơi lại</button>
    </div>
</div>
{% endblock %}
{% block scripts %}
{{ super() }}
<script>
(function() {
    var score = 0;
    var total = {{ game.total }};
    var selectedLeft = null;
    var selectedRight = null;
    var cards = document.querySelectorAll('.match-card');
    cards.forEach(function(card) {
        card.addEventListener('click', function() {
            if (card.classList.contains('matched')) return;
            var side = card.dataset.side;
            if (side === 'left') {
                if (selectedLeft) selectedLeft.classList.remove('selected');
                selectedLeft = card;
                card.classList.add('selected');
            } else {
                if (selectedRight) selectedRight.classList.remove('selected');
                selectedRight = card;
                card.classList.add('selected');
            }
            if (selectedLeft && selectedRight) {
                checkMatch();
            }
        });
    });
    function checkMatch() {
        var leftItemId = selectedLeft.dataset.itemId;
        var rightItemId = selectedRight.dataset.itemId;
        if (leftItemId === rightItemId) {
            selectedLeft.classList.remove('selected');
            selectedRight.classList.remove('selected');
            selectedLeft.classList.add('matched');
            selectedRight.classList.add('matched');
            score++;
            document.getElementById('score').textContent = score;
            selectedLeft = null;
            selectedRight = null;
            if (score === total) {
                setTimeout(function() {
                    document.getElementById('final-score').textContent = score;
                    document.getElementById('complete-modal').style.display = 'flex';
                }, 300);
            }
        } else {
            selectedLeft.classList.add('wrong');
            selectedRight.classList.add('wrong');
            setTimeout(function() {
                selectedLeft.classList.remove('wrong', 'selected');
                selectedRight.classList.remove('wrong', 'selected');
                selectedLeft = null;
                selectedRight = null;
            }, 500);
        }
    }
})();
</script>
{% endblock %}'''

mcq_path = r"c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\mcq\templates\mcq\session.html"
typing_path = r"c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\typing\templates\typing\session.html"
matching_path = r"c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\matching\templates\matching\session.html"

def write(path, content):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"SUCCESS: Wrote {path}")
    except Exception as e:
        print(f"ERROR: Failed to write {path}: {e}")

write(mcq_path, mcq_content)
write(typing_path, typing_content)
write(matching_path, matching_content)
