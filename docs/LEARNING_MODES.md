# MindStack Learning Modes

## Overview

MindStack hỗ trợ nhiều chế độ học để phù hợp với mục tiêu khác nhau.

---

## Flashcard Mode

**Mục đích**: Ôn tập với spaced repetition

| Aspect | Details |
|--------|---------|
| Input | Xem mặt trước → tự recall → lật xem đáp án |
| Rating | 3-6 buttons (Quên/Mơ hồ/Nhớ/Dễ) |
| SRS | Full SM-2 với interval scheduling |

**Use cases**: Vocabulary, facts, definitions

---

## Quiz/MCQ Mode

**Mục đích**: Kiểm tra kiến thức với multiple choice

| Aspect | Details |
|--------|---------|
| Input | Chọn 1 trong 4 đáp án |
| Scoring | Correct → quality 4, Wrong → quality 1 |
| SRS | Binary outcome mapping |

**Use cases**: Exam prep, certification study

---

## Typing Mode

**Mục đích**: Active recall qua viết

| Aspect | Details |
|--------|---------|
| Input | Gõ câu trả lời |
| Scoring | Based on accuracy % |
| SRS | ≥100% → 5, ≥85% → 4, else → 1 |

**Use cases**: Spelling, vocabulary, language learning

---

## Listening Mode

**Mục đích**: Nghe và gõ lại

| Aspect | Details |
|--------|---------|
| Input | Nghe audio → gõ transcript |
| Scoring | Same as Typing mode |
| Features | TTS auto-generated |

**Use cases**: Listening comprehension, dictation

---

## Speed Mode

**Mục đích**: Quick review nhiều items

| Aspect | Details |
|--------|---------|
| Input | Yes/No biết hay không |
| Scoring | Simplified |
| Pace | Fast, no SRS scheduling |

**Use cases**: Warm-up, overview review

---

## Matching Mode

**Mục đích**: Kết nối pairs

| Aspect | Details |
|--------|---------|
| Input | Drag & drop matching |
| Scoring | Based on correct pairs |
| Batch | Multiple items per round |

**Use cases**: Term-definition, translation pairs

---

## Mode Comparison

| Mode | Cognitive Load | Best For |
|------|----------------|----------|
| Flashcard | Medium | Daily review |
| MCQ | Low | Testing |
| Typing | High | Deep learning |
| Listening | High | Language |
| Speed | Low | Quick check |
| Matching | Medium | Association |

---

## Cognitive Load Heuristic

SRS quality được normalize dựa trên cognitive load:

```
High Load (Typing/Listening):
  Perfect    → quality 5
  Good (85%+) → quality 4
  Fail       → quality 1

Low Load (MCQ/Matching):
  Correct → quality 4
  Wrong   → quality 1
```

Modes với cognitive load cao hơn được thưởng điểm cao hơn.
