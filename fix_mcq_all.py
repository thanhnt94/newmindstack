"""
Fix MCQ setup.html - Apply all changes atomically:
1. Remove stats section
2. Add default pair in HTML
3. Fix split Jinja lines
4. Remove duplicate addPair init call
"""

path = r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\vocabulary\mcq\templates\mcq\setup.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove stats section (from <!-- Learning Statistics --> to the closing </div>\n\n before Question-Answer)
stats_start = '            <!-- Learning Statistics -->'
stats_end = '''            </div>

            <!-- Question-Answer Pairs Section -->'''
replacement_1 = '''            <!-- Question-Answer Pairs Section -->'''
content = content.replace(stats_start, '', 1)
content = content.replace('''                </div>
            </div>

            <!-- Question-Answer Pairs Section -->''', '            <!-- Question-Answer Pairs Section -->', 1)

# Actually, do a simpler replace - find the entire stats block
stats_block = '''            <!-- Learning Statistics -->
            <div class="setup-section">
                <span class="setup-label">
                    <i class="fas fa-chart-bar"></i>
                    Thống kê học tập
                </span>
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-value new">{{ mode_counts.new }}</span>
                        <span class="stat-label">Từ mới</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value due">{{ mode_counts.due }}</span>
                        <span class="stat-label">Cần ôn tập</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value learned">{{ mode_counts.learned }}</span>
                        <span class="stat-label">Đã học</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value total">{{ mode_counts.total }}</span>
                        <span class="stat-label">Tổng số</span>
                    </div>
                </div>
            </div>

'''
content = content.replace(stats_block, '', 1)

# 2. Replace pairs-container comment with default pair
old_pairs = '''                <div class="pairs-container" id="pairs-container">
                    <!-- Pairs added by JS -->
                </div>'''

new_pairs = '''                <div class="pairs-container" id="pairs-container">
                    <!-- Default pair: front -> back -->
                    <div class="pair-row" data-pair-index="0">
                        <div class="pair-col">
                            <div class="pair-col-label">Câu hỏi</div>
                            <select class="pair-q">
                                <option value="">-- Chọn cột --</option>
                                {% for key in available_keys %}
                                <option value="{{ key }}"{% if key == 'front' %} selected{% endif %}>{{ key }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <span class="pair-arrow"><i class="fas fa-arrow-right"></i></span>
                        <div class="pair-col">
                            <div class="pair-col-label">Đáp án</div>
                            <select class="pair-a">
                                <option value="">-- Chọn cột --</option>
                                {% for key in available_keys %}
                                <option value="{{ key }}"{% if key == 'back' %} selected{% endif %}>{{ key }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <button type="button" class="pair-delete"><i class="fas fa-times"></i></button>
                    </div>
                </div>'''
content = content.replace(old_pairs, new_pairs, 1)

# 3. Remove addPair init call (default pair is now in HTML)
old_init = '''    // Initialize with default pair (front -> back)
    addPair('front', 'back');'''
new_init = '''    // Default pair is already in HTML - attach delete event to existing row
    document.querySelectorAll('.pair-delete').forEach(function(btn) {
        btn.addEventListener('click', function() {
            this.closest('.pair-row').remove();
        });
    });'''
content = content.replace(old_init, new_init, 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('All changes applied successfully!')

# Verify key lines
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines, 1):
        if 'container.container_id' in line:
            print(f'Line {i}: {line.strip()[:80]}')
        if 'total_items' in line:
            print(f'Line {i}: {line.strip()[:80]}')
