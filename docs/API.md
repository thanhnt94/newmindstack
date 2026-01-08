# MindStack API Documentation

## Overview

All API endpoints use JSON for request/response bodies unless otherwise noted.
Authentication is required for most endpoints (Flask-Login session-based).

---

## Learning - Flashcard

### Session API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/flashcard/set/<set_id>/session` | Start flashcard session |
| POST | `/flashcard/api/batch` | Get next card batch |
| POST | `/flashcard/api/submit` | Submit card rating |
| POST | `/flashcard/api/end-session` | End current session |

### Item API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/flashcard/item/<item_id>` | Get item details |
| POST | `/flashcard/item/<item_id>/note` | Save user note |
| POST | `/flashcard/item/<item_id>/ai-explain` | Generate AI explanation |

---

## Learning - Quiz

### Session API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/quiz/set/<set_id>/session` | Start quiz session |
| POST | `/quiz/api/batch` | Get question batch |
| POST | `/quiz/api/submit` | Submit answer batch |

### Battle API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/quiz/battle/create` | Create battle room |
| POST | `/quiz/battle/<room_code>/join` | Join battle room |
| POST | `/quiz/battle/<room_code>/submit/<seq>` | Submit round answer |

---

## Learning - Vocabulary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/vocab/mcq/set/<set_id>` | MCQ mode session |
| GET | `/vocab/typing/set/<set_id>` | Typing mode session |
| GET | `/vocab/listening/set/<set_id>` | Listening mode session |
| GET | `/vocab/speed/set/<set_id>` | Speed mode session |

---

## Statistics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stats/api/item/<item_id>` | Item statistics |
| GET | `/stats/api/set/<set_id>` | Set statistics |
| POST | `/stats/api/history/<log_type>` | Get review history |

---

## Gamification

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/gamification/points` | Points settings (admin) |
| GET | `/gamification/badges` | List badges (admin) |
| POST | `/gamification/badges/new` | Create badge (admin) |

---

## AI Services

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ai/explain` | Generate AI explanation |
| GET | `/ai/models` | List available models |

---

## User

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | User login |
| POST | `/auth/logout` | User logout |
| GET | `/profile` | User profile |

---

## Common Response Format

**Success:**
```json
{
  "success": true,
  "data": { ... }
}
```

**Error:**
```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

---

## Authentication

Most endpoints require authentication via Flask-Login session cookie.
Admin endpoints require `user_role == 'admin'`.
