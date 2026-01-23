# MindStack Changelog

Tất cả thay đổi quan trọng của dự án được ghi nhận tại đây.

Format dựa trên [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
và tuân theo [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### 🚀 Added
- **Database-Backed Session Management**: Chuyển đổi quản lý phiên học sang database để hỗ trợ cross-device persistence (resume session).
- **LearningSession Model**: Model mới lưu trữ trạng thái chi tiết của từng phiên học.
- **Active Session API**: Endpoint mới để kiểm tra phiên học đang hoạt động.
- Thêm documentation toàn diện (DEPLOYMENT, CHANGELOG, TROUBLESHOOTING, ...)

### ♻️ Changed
- **Gamification Module Refactor**: Tái cấu trúc theo kiến trúc 3 tầng (Logic - Service - Route)
  - Tạo `logics/streak_logic.py` với pure functions cho streak calculation
  - Thêm signal `score_awarded` để decoupling giữa ScoreService và BadgeService
  - Loại bỏ circular dependency bằng signal-based communication
- **Learning Module Refactor**: Tái cấu trúc theo kiến trúc 3 tầng
  - Tạo `logics/session_logic.py` với pure functions cho session building (filter, sort, queue)
  - Thêm `card_reviewed.send()` trong `fsrs_service.py` để emit signals cho gamification
- **Content Management Module Refactor**: Tái cấu trúc theo kiến trúc 3 tầng
  - Tạo `logics/parsers.py` với pure functions cho column classification, action normalization
  - Thêm signals `content_created`, `content_deleted` cho event broadcasting
  - Emit signal trong `FlashcardExcelService` sau khi import thành công
- **Notification Module Refactor**: Chuyển sang event-driven architecture
  - Tạo `events.py` với listeners cho `content_created` và `score_awarded`
  - Notifications tự động trigger khi có events (import thành công, đạt milestone điểm)

---

## [1.6.0] - 2026-01-12

### 🚀 Added
- **BBCode Support**: Hỗ trợ BBCode formatting cho tất cả content fields
  - Flashcard: `front`, `back`, `ai_explanation`
  - Quiz: `question`, `options`, `explanation`, `note_content`
  - Vocabulary modes: MCQ, Typing, Listening
  - Docs: [BBCODE.md](BBCODE.md)
- **ReviewLog Session Context**: Thêm 4 columns mới cho analytics
  - `session_id`, `container_id`, `mode`, `streak_position`
- **Flask-Migrate Setup**: Khởi tạo hệ thống migrations đúng cách
- **strip_bbcode()**: Hàm loại bỏ BBCode khi validate answer (Typing/Listening)

### 🐛 Fixed
- Sửa orphaned alembic revision từ migrations archive cũ
- Answer validation giờ đây tự động strip BBCode tags

### ♻️ Changed
- Cấu trúc `content_renderer.py` với `render_text_field()` và `render_content_dict()`


## [1.5.0] - 2026-01-08

### 🚀 Added
- **Quiz Stats Enhancement**: Hiển thị `user_answer` và `duration_ms` trong history
- **Edit Button**: Thêm nút "Edit Card" trong stats modal
- **AI Markdown**: Markdown rendering cho AI explanations

### 🐛 Fixed
- Sửa lỗi Markdown rendering trong Quiz/Vocabulary modals
- Sửa lỗi notes section hiển thị không đúng
- Sửa `jinja2.exceptions.UndefinedError: 'permissions'`

### ♻️ Changed
- Refactor notification components thành HTML partials riêng biệt
- Cải thiện mobile header buttons

---

## [1.4.0] - 2026-01-04

### 🚀 Added
- **Session Sync**: Hỗ trợ session synchronization và resume
- **Short Session IDs**: Session IDs ngắn gọn hơn cho URL
- **Active Batch Cache**: Cache batch data để tối ưu performance

### 🐛 Fixed
- Sửa `NameError: name 'datetime' is not defined` trong `session_logic.py`
- Sửa lỗi default config không lưu được trong Set Editor

### ♻️ Changed
- Thêm dedicated "Lưu Cấu hình" button cho Set Editor

---

## [1.3.0] - 2026-01-03

### 🚀 Added
- **Cute Game Notifications**: Redesign score/mastery notifications với game-like aesthetic

### 🐛 Fixed
- Sửa MCQ layout shrinkage issue
- Sửa `SyntaxError` trong flashcard session JavaScript

### ♻️ Changed
- Extract Memory Power và Score Toast thành reusable partials

---

## [1.2.0] - 2026-01-02

### ♻️ Changed
- **Flashcard Assets Refactor**: Extract inline CSS/JS thành external files
- Tạo `mobile_ui.js` cho mobile interactions
- Tổ chức lại folder structure cho flashcard templates

### 🐛 Fixed
- Sửa rating buttons không hiển thị trên card back
- Sửa desktop card UI không load được
- Sửa variable redeclaration trong JavaScript

---

## [1.1.0] - 2025-12-31

### ♻️ Changed
- **Codebase Cleanup**: Xóa legacy modules (`modules/main`)
- Consolidate learning module structure
- Synchronize template styles với Flashcard V2

### 🐛 Fixed
- Sửa blank dashboard page
- Sửa CSS issues cho mobile/desktop views

---

## [1.0.0] - 2025-12-30

### 🚀 Added
- **Core Learning Modes**: Flashcard, Quiz, MCQ, Typing, Listening, Speed, Matching
- **SRS System**: Hybrid SM-2 + Memory Power
- **Gamification**: Points, streaks, badges, leaderboard
- **AI Integration**: Gemini + HuggingFace cho AI explanations
- **Statistics**: Dashboard, item stats, review history

---

## Version Legend

| Type | Icon | Description |
|------|------|-------------|
| Added | 🚀 | Tính năng mới |
| Changed | ♻️ | Thay đổi existing functionality |
| Deprecated | ⚠️ | Tính năng sắp bị loại bỏ |
| Removed | 🗑️ | Tính năng đã bị loại bỏ |
| Fixed | 🐛 | Bug fixes |
| Security | 🔒 | Security updates |

---

## How to Update Changelog

1. Thêm changes mới vào section `[Unreleased]`
2. Khi release version mới:
   - Đổi `[Unreleased]` thành `[X.Y.Z] - YYYY-MM-DD`
   - Tạo section `[Unreleased]` mới ở trên

```markdown
## [Unreleased]

### 🚀 Added
- New feature description

## [1.6.0] - 2026-01-15
...
```
