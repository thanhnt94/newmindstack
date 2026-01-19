# MindStack SRS Algorithm (Spec v8)

## Overview

MindStack sử dụng **Custom SRS Spec v8** với 5 trạng thái và thang điểm 0-7.

---

## Part 1: Thang Điểm (0-7)

| Nguồn | Điểm |
|-------|------|
| Flashcard (nút) | 0, 1, 2, 3, 4, 5 |
| Trắc nghiệm Sai | 1 |
| Trắc nghiệm Đúng | 6 |
| Typing Sai | 1 |
| Typing Đúng | 7 |

---

## Part 2: State Machine (5 Trạng Thái)

```
NEW → LEARNING → REVIEW ↔ HARD → MASTER
```

### A. NEW (Khởi tạo)
- **Khi**: `reps = 0`
- **Hành động**: Chuyển sang LEARNING, `interval = 20 phút`

### B. LEARNING (Phút)
- **Sàn**: 20 phút
- **Tốt nghiệp**: > 2880 phút (2 ngày) → REVIEW
- **Safety Valve**: `reps >= 10` mà chưa tốt nghiệp → HARD

| Score | Công thức |
|-------|-----------|
| 0 | 20.0 (về sàn) |
| 1 | max(20, x * 0.5) |
| 2 | max(20, x * 0.8) (PHẠT) |
| 3 | max(20, x * 1.5) |
| 4 | max(20, x * 2.5) |
| 5 | max(20, x * 4.0) |
| 6 | max(20, x * 5.0) |
| 7 | max(20, x * 7.0) |

### C. REVIEW (Ngày)
- **Trần**: 365 ngày
- **Thất bại** (0, 1): → HARD
- **Thăng hạng**: Streak ≥ 10 → MASTER

| Score | Hệ số |
|-------|-------|
| 2 | x 0.8 (PHẠT) |
| 3 | x 1.8 |
| 4 | x 2.5 |
| 5 | x 3.5 |
| 6 | x 4.5 |
| 7 | x 6.0 |

### D. HARD (Ngày)
- **Vào**: Từ REVIEW khi Score 0/1 hoặc "Mark as Hard"
- **Thoát**: `Hard_Streak >= 3` → REVIEW

| Score | Công thức | Hard_Streak |
|-------|-----------|-------------|
| 0-1 | 1.0 ngày | Reset = 0 |
| 2 | x 0.8 | Reset = 0 |
| 3 | x 1.2 | Giữ nguyên |
| 4-5 | x 1.3 | +1 |
| 6 | x 1.4 | +1 |
| 7 | x 1.5 | +1 |

### E. MASTER (Ngày)
- **Bonus**: Hệ số REVIEW x 1.2
- **Soft Demotion** (Score 0, 1, 2): về REVIEW với `max(3, x * 0.5)`

---

## Code References

- [`memory_engine.py`](../mindstack_app/modules/learning/logics/memory_engine.py) - Core engine
- [`unified_srs.py`](../mindstack_app/modules/learning/logics/unified_srs.py) - Unified interface
- [`srs_service.py`](../mindstack_app/modules/learning/services/srs_service.py) - Service layer
