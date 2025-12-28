# Database Schema Review
# Generated: 2025-12-28
# Total Tables: 38

## ai_logs (29 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| log_id | INTEGER | PK, NOT NULL |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| user_id | INTEGER | - |
| provider | VARCHAR(50) | NOT NULL |
| model_name | VARCHAR(100) | NOT NULL |
| key_id | INTEGER | - |
| request_type | VARCHAR(50) | - |
| item_info | VARCHAR(255) | - |
| prompt_chars | INTEGER | - |
| response_chars | INTEGER | - |
| processing_time_ms | INTEGER | - |
| status | VARCHAR(20) | - |
| error_message | TEXT | - |

## api_keys (2 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| key_id | INTEGER | PK, NOT NULL |
| key_value | VARCHAR(255) | NOT NULL |
| is_active | BOOLEAN | - |
| is_exhausted | BOOLEAN | - |
| last_used_timestamp | DATETIME | - |
| notes | TEXT | - |
| provider | VARCHAR(50) | NOT NULL, DEFAULT 'gemini' |

## app_settings (37 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| key | VARCHAR(100) | PK, NOT NULL |
| value | JSON | NOT NULL |
| category | VARCHAR(50) | - |
| data_type | VARCHAR(50) | - |
| description | TEXT | - |
| updated_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| updated_by | INTEGER | - |

## background_task_logs (64 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| log_id | INTEGER | PK, NOT NULL |
| task_id | INTEGER | NOT NULL |
| task_name | VARCHAR(100) | NOT NULL |
| status | VARCHAR(50) | NOT NULL |
| progress | INTEGER | - |
| total | INTEGER | - |
| message | TEXT | - |
| stop_requested | BOOLEAN | - |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

## background_tasks (7 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| task_id | INTEGER | PK, NOT NULL |
| task_name | VARCHAR(100) | NOT NULL |
| status | VARCHAR(50) | - |
| progress | INTEGER | - |
| total | INTEGER | - |
| message | TEXT | - |
| stop_requested | BOOLEAN | - |
| is_enabled | BOOLEAN | - |
| last_updated | DATETIME | - |

## badges (5 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| badge_id | INTEGER | PK, NOT NULL |
| name | VARCHAR(100) | NOT NULL |
| description | VARCHAR(255) | - |
| icon_class | VARCHAR(50) | - |
| condition_type | VARCHAR(50) | NOT NULL |
| condition_value | INTEGER | NOT NULL |
| reward_points | INTEGER | - |
| is_active | BOOLEAN | - |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

## container_contributors (0 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| contributor_id | INTEGER | PK, NOT NULL |
| container_id | INTEGER | NOT NULL |
| user_id | INTEGER | NOT NULL |
| permission_level | VARCHAR(50) | NOT NULL |
| granted_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

## course_progress (0 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| progress_id | INTEGER | PK, NOT NULL |
| user_id | INTEGER | NOT NULL |
| item_id | INTEGER | NOT NULL |
| completion_percentage | INTEGER | NOT NULL |
| last_updated | DATETIME | DEFAULT CURRENT_TIMESTAMP |

## flashcard_collab_answers (5 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| answer_id | INTEGER | PK, NOT NULL |
| round_id | INTEGER | NOT NULL |
| user_id | INTEGER | NOT NULL |
| answer_label | VARCHAR(50) | - |
| answer_quality | INTEGER | - |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | - |

## flashcard_collab_messages (2 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| message_id | INTEGER | PK, NOT NULL |
| room_id | INTEGER | NOT NULL |
| user_id | INTEGER | NOT NULL |
| content | TEXT | NOT NULL |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP |

## flashcard_collab_participants (1 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| participant_id | INTEGER | PK, NOT NULL |
| room_id | INTEGER | NOT NULL |
| user_id | INTEGER | NOT NULL |
| is_host | BOOLEAN | NOT NULL |
| status | VARCHAR(20) | NOT NULL |
| joined_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| left_at | DATETIME | - |

## flashcard_collab_rooms (1 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| room_id | INTEGER | PK, NOT NULL |
| room_code | VARCHAR(12) | NOT NULL |
| title | VARCHAR(120) | NOT NULL |
| host_user_id | INTEGER | NOT NULL |
| container_id | INTEGER | NOT NULL |
| mode | VARCHAR(50) | NOT NULL |
| button_count | INTEGER | NOT NULL |
| status | VARCHAR(20) | NOT NULL |
| is_public | BOOLEAN | NOT NULL |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | - |

## flashcard_collab_rounds (6 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| round_id | INTEGER | PK, NOT NULL |
| room_id | INTEGER | NOT NULL |
| item_id | INTEGER | NOT NULL |
| status | VARCHAR(20) | NOT NULL |
| scheduled_for_user_id | INTEGER | - |
| scheduled_due_at | DATETIME | - |
| started_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| completed_at | DATETIME | - |

## flashcard_progress (55 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| progress_id | INTEGER | PK |
| user_id | INTEGER | NOT NULL |
| item_id | INTEGER | NOT NULL |
| due_time | DATETIME | - |
| easiness_factor | FLOAT | - |
| repetitions | INTEGER | - |
| interval | INTEGER | - |
| last_reviewed | DATETIME | - |
| status | VARCHAR(50) | - |
| times_correct | INTEGER | - |
| times_incorrect | INTEGER | - |
| times_vague | INTEGER | - |
| correct_streak | INTEGER | - |
| incorrect_streak | INTEGER | - |
| vague_streak | INTEGER | - |
| first_seen_timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| mastery | REAL | DEFAULT 0.0 |

## flashcard_room_progress (5 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| progress_id | INTEGER | PK, NOT NULL |
| room_id | INTEGER | NOT NULL |
| item_id | INTEGER | NOT NULL |
| status | VARCHAR(20) | NOT NULL |
| due_time | DATETIME | - |
| interval | INTEGER | - |
| easiness_factor | FLOAT | - |
| repetitions | INTEGER | - |
| last_reviewed | DATETIME | - |

## goal_daily_history (119 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| history_id | INTEGER | PK, NOT NULL |
| goal_id | INTEGER | NOT NULL |
| date | DATE | NOT NULL |
| current_value | INTEGER | - |
| target_value | INTEGER | - |
| is_met | BOOLEAN | - |
| updated_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

## learning_containers (16 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| container_id | INTEGER | PK, NOT NULL |
| creator_user_id | INTEGER | NOT NULL |
| container_type | VARCHAR(50) | NOT NULL |
| title | VARCHAR(255) | NOT NULL |
| description | TEXT | - |
| cover_image | VARCHAR(512) | - |
| tags | VARCHAR(255) | - |
| is_public | BOOLEAN | NOT NULL |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | - |
| ai_prompt | TEXT | - |
| ai_capabilities | JSON | - |
| media_image_folder | VARCHAR(255) | - |
| media_audio_folder | VARCHAR(255) | - |
| ai_settings | JSON | - |

## learning_goals (7 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| goal_id | INTEGER | PK, NOT NULL |
| user_id | INTEGER | NOT NULL |
| goal_type | VARCHAR(50) | NOT NULL |
| period | VARCHAR(20) | NOT NULL |
| target_value | INTEGER | NOT NULL |
| title | VARCHAR(120) | - |
| description | TEXT | - |
| start_date | DATE | - |
| due_date | DATE | - |
| notes | TEXT | - |
| is_active | BOOLEAN | NOT NULL |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | - |
| reference_id | INTEGER | - |
| domain | VARCHAR(50) | DEFAULT 'general' |
| scope | VARCHAR(50) | DEFAULT 'global' |
| metric | VARCHAR(50) | DEFAULT 'points' |

## learning_groups (54 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| group_id | INTEGER | PK, NOT NULL |
| container_id | INTEGER | NOT NULL |
| group_type | VARCHAR(50) | NOT NULL |
| content | JSON | NOT NULL |

## learning_items (12693 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| item_id | INTEGER | PK, NOT NULL |
| container_id | INTEGER | NOT NULL |
| group_id | INTEGER | - |
| item_type | VARCHAR(50) | NOT NULL |
| content | JSON | NOT NULL |
| order_in_container | INTEGER | - |
| ai_explanation | TEXT | - |
| search_text | TEXT | - |

## learning_progress (335 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| progress_id | INTEGER | PK, NOT NULL |
| user_id | INTEGER | NOT NULL |
| item_id | INTEGER | NOT NULL |
| learning_mode | VARCHAR(20) | NOT NULL |
| status | VARCHAR(50) | - |
| due_time | DATETIME | - |
| easiness_factor | FLOAT | - |
| interval | INTEGER | - |
| repetitions | INTEGER | - |
| last_reviewed | DATETIME | - |
| first_seen | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| mastery | FLOAT | - |
| times_correct | INTEGER | - |
| times_incorrect | INTEGER | - |
| times_vague | INTEGER | - |
| correct_streak | INTEGER | - |
| incorrect_streak | INTEGER | - |
| vague_streak | INTEGER | - |
| mode_data | JSON | - |

## memrise_progress (9 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| progress_id | INTEGER | PK, NOT NULL |
| user_id | INTEGER | NOT NULL |
| item_id | INTEGER | NOT NULL |
| memory_level | INTEGER | NOT NULL |
| due_time | DATETIME | - |
| interval | INTEGER | - |
| times_correct | INTEGER | NOT NULL |
| times_incorrect | INTEGER | NOT NULL |
| last_reviewed | DATETIME | - |
| first_seen | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| current_streak | INTEGER | NOT NULL |
| session_reps | INTEGER | NOT NULL |

## notifications (0 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, NOT NULL |
| user_id | INTEGER | NOT NULL |
| type | VARCHAR(50) | - |
| title | VARCHAR(255) | NOT NULL |
| message | TEXT | - |
| link | VARCHAR(500) | - |
| is_read | BOOLEAN | - |
| created_at | DATETIME | - |
| meta_data | JSON | - |

## push_subscriptions (2 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, NOT NULL |
| user_id | INTEGER | NOT NULL |
| endpoint | VARCHAR(500) | NOT NULL |
| auth_key | VARCHAR(200) | NOT NULL |
| p256dh_key | VARCHAR(200) | NOT NULL |
| created_at | DATETIME | - |

## quiz_battle_answers (76 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| answer_id | INTEGER | PK, NOT NULL |
| round_id | INTEGER | NOT NULL |
| participant_id | INTEGER | NOT NULL |
| selected_option | VARCHAR(5) | NOT NULL |
| is_correct | BOOLEAN | NOT NULL |
| score_delta | INTEGER | NOT NULL |
| correct_option | VARCHAR(5) | - |
| explanation | TEXT | - |
| answered_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

## quiz_battle_messages (18 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| message_id | INTEGER | PK, NOT NULL |
| room_id | INTEGER | NOT NULL |
| user_id | INTEGER | NOT NULL |
| content | TEXT | NOT NULL |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP |

## quiz_battle_participants (6 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| participant_id | INTEGER | PK, NOT NULL |
| room_id | INTEGER | NOT NULL |
| user_id | INTEGER | NOT NULL |
| is_host | BOOLEAN | NOT NULL |
| status | VARCHAR(20) | NOT NULL |
| joined_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| left_at | DATETIME | - |
| kicked_by | INTEGER | - |
| session_score | INTEGER | NOT NULL |
| correct_answers | INTEGER | NOT NULL |
| incorrect_answers | INTEGER | NOT NULL |

## quiz_battle_rooms (3 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| room_id | INTEGER | PK, NOT NULL |
| room_code | VARCHAR(12) | NOT NULL |
| title | VARCHAR(120) | NOT NULL |
| host_user_id | INTEGER | NOT NULL |
| container_id | INTEGER | NOT NULL |
| status | VARCHAR(20) | NOT NULL |
| is_locked | BOOLEAN | NOT NULL |
| max_players | INTEGER | - |
| question_limit | INTEGER | - |
| is_public | BOOLEAN | NOT NULL |
| mode | VARCHAR(20) | NOT NULL |
| time_per_question_seconds | INTEGER | - |
| question_order | JSON | - |
| current_round_number | INTEGER | NOT NULL |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | - |

## quiz_battle_rounds (45 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| round_id | INTEGER | PK, NOT NULL |
| room_id | INTEGER | NOT NULL |
| sequence_number | INTEGER | NOT NULL |
| item_id | INTEGER | NOT NULL |
| status | VARCHAR(20) | NOT NULL |
| started_at | DATETIME | - |
| ended_at | DATETIME | - |

## quiz_progress (271 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| progress_id | INTEGER | PK |
| user_id | INTEGER | NOT NULL |
| item_id | INTEGER | NOT NULL |
| times_correct | INTEGER | - |
| times_incorrect | INTEGER | - |
| correct_streak | INTEGER | - |
| incorrect_streak | INTEGER | - |
| last_reviewed | DATETIME | - |
| status | VARCHAR(50) | - |
| first_seen_timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| mastery | REAL | DEFAULT 0.0 |

## review_logs (595 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| log_id | INTEGER | PK, NOT NULL |
| user_id | INTEGER | NOT NULL |
| item_id | INTEGER | NOT NULL |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| rating | INTEGER | NOT NULL |
| duration_ms | INTEGER | - |
| interval | INTEGER | - |
| easiness_factor | FLOAT | - |
| review_type | VARCHAR(20) | - |
| user_answer | VARCHAR(10) | - |
| is_correct | BOOLEAN | - |
| score_change | INTEGER | - |
| mastery_snapshot | REAL | - |
| memory_power_snapshot | REAL | - |

## score_logs (506 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| log_id | INTEGER | PK, NOT NULL |
| user_id | INTEGER | NOT NULL |
| item_id | INTEGER | - |
| score_change | INTEGER | NOT NULL |
| reason | VARCHAR(100) | - |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| item_type | VARCHAR(50) | - |

## user_badges (5 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, NOT NULL |
| user_id | INTEGER | NOT NULL |
| badge_id | INTEGER | NOT NULL |
| earned_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

## user_container_states (19 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, NOT NULL |
| user_id | INTEGER | NOT NULL |
| container_id | INTEGER | NOT NULL |
| is_archived | BOOLEAN | NOT NULL |
| is_favorite | BOOLEAN | NOT NULL |
| last_accessed | DATETIME | DEFAULT CURRENT_TIMESTAMP |

## user_feedback (1 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| feedback_id | INTEGER | PK, NOT NULL |
| user_id | INTEGER | NOT NULL |
| item_id | INTEGER | - |
| recipient_id | INTEGER | - |
| content | TEXT | NOT NULL |
| status | VARCHAR(50) | - |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| resolved_by_id | INTEGER | - |

## user_notes (10 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| note_id | INTEGER | PK, NOT NULL |
| user_id | INTEGER | NOT NULL |
| item_id | INTEGER | NOT NULL |
| content | TEXT | NOT NULL |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

## user_sessions (8 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| user_id | INTEGER | PK, NOT NULL |
| current_flashcard_container_id | INTEGER | - |
| current_quiz_container_id | INTEGER | - |
| current_course_container_id | INTEGER | - |
| current_flashcard_mode | VARCHAR(50) | - |
| current_quiz_mode | VARCHAR(50) | - |
| current_quiz_batch_size | INTEGER | - |
| flashcard_button_count | INTEGER | - |
| last_updated | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| flashcard_theme | VARCHAR(50) | DEFAULT 'default' |

## users (8 rows)
| Column | Type | Constraints |
|--------|------|-------------|
| user_id | INTEGER | PK |
| username | VARCHAR(80) | NOT NULL |
| email | VARCHAR(120) | NOT NULL |
| password_hash | VARCHAR(256) | NOT NULL |
| user_role | VARCHAR(50) | NOT NULL |
| total_score | INTEGER | - |
| last_seen | DATETIME | - |
| telegram_chat_id | VARCHAR(100) | - |
| timezone | VARCHAR(50) | DEFAULT 'UTC' |
| last_preferences | TEXT | DEFAULT '{}' |
