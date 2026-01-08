# MindStack

**Ứng dụng học tập thông minh với Spaced Repetition, Gamification và AI**

## ✨ Tính Năng

- 🧠 **Đa chế độ học**: Flashcard, Quiz, MCQ, Typing, Listening, Speed, Matching
- 📊 **SRS thông minh**: Hybrid SM-2 + Memory Power System
- 🎮 **Gamification**: Điểm, badges, streak, leaderboard
- 🤖 **AI tích hợp**: Giải thích nội dung, gợi ý học tập

## 📁 Documentation

| Doc | Description |
|-----|-------------|
| [Architecture](docs/ARCHITECTURE.md) | Kiến trúc tổng quan |
| [API Reference](docs/API.md) | Danh sách endpoints |
| [SRS Algorithm](docs/SRS_ALGORITHM.md) | Chi tiết thuật toán SRS |
| [Gamification](docs/GAMIFICATION.md) | Hệ thống điểm, badges |
| [Learning Modes](docs/LEARNING_MODES.md) | Các chế độ học |
| [Database](docs/DATABASE.md) | Schema database |
| [Contributing](docs/CONTRIBUTING.md) | Hướng dẫn đóng góp |
| [Deployment](docs/DEPLOYMENT.md) | Hướng dẫn deploy production |
| [Changelog](docs/CHANGELOG.md) | Lịch sử phiên bản |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Xử lý lỗi thường gặp |
| [AI Integration](docs/AI_INTEGRATION.md) | Tích hợp AI (Gemini, HuggingFace) |
| [Session Management](docs/SESSION_MANAGEMENT.md) | Quản lý sessions học |
| [Configuration](docs/CONFIGURATION.md) | Cấu hình môi trường |
| [Testing](docs/TESTING.md) | Hướng dẫn testing |
| [UI Components](docs/UI_COMPONENTS.md) | Thư viện UI components |
| [Security](docs/SECURITY.md) | Bảo mật ứng dụng |

---

## 🚀 Cài đặt

### Yêu cầu
- Python 3.12+ (khuyến nghị) hoặc Python 3.13

### Các bước

1. **Tạo môi trường ảo:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

2. **Cài đặt dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   > Nếu dùng Python 3.13, gói `audioop-lts` sẽ tự động được cài.

3. **Chạy ứng dụng:**
   ```bash
   python start_mindstack_app.py
   ```

---

## 🧪 Testing

```bash
python -m pytest tests/ -v
```

---

## 📂 Project Structure

```
mindstack_app/
├── models/       # Database models
├── modules/      # Feature modules (learning, gamification, ...)
├── services/     # Shared services
└── templates/    # Jinja2 templates
```

Xem chi tiết tại [ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 🤝 Contributing

1. Fork repository
2. Tạo branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m 'Add feature'`
4. Push: `git push origin feature/my-feature`
5. Open Pull Request
