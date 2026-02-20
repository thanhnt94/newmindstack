# Tài liệu Cấu trúc Cơ sở dữ liệu MindStack (Auto-generated)

Tài liệu này liệt kê các Database Models và Columns, được trích xuất tự động qua AST từ tất cả `models.py`.

## Module: `AI`

### Model: `ApiKey`
- **`key_id`**: (Integer)
- **`provider`**
- **`key_value`**
- **`is_active`**: (Boolean)
- **`is_exhausted`**: (Boolean)
- **`last_used_timestamp`**
- **`notes`**: (Text)

### Model: `AiTokenLog`
- **`log_id`**: (Integer)
- **`timestamp`**
- **`user_id`**: (Integer)
- **`provider`**
- **`model_name`**
- **`key_id`**: (Integer)
- **`feature`**
- **`context_ref`**
- **`input_tokens`**: (Integer)
- **`output_tokens`**: (Integer)
- **`processing_time_ms`**: (Integer)
- **`status`**
- **`error_message`**: (Text)

### Model: `AiCache`
- **`cache_id`**: (Integer)
- **`provider`**
- **`model_name`**
- **`prompt_hash`**
- **`response_text`**: (Text)
- **`created_at`**
- **`expires_at`**
- **`hit_count`**: (Integer)
- **`last_hit_at`**

### Model: `AiContent`
- **`content_id`**: (Integer)
- **`item_id`**: (Integer)
- **`content_type`**
- **`provider`**
- **`model_name`**
- **`user_question`**: (Text)
- **`prompt`**: (Text)
- **`content_text`**: (Text)
- **`created_at`**
- **`user_id`**: (Integer)
- **`is_primary`**: (Boolean)
- **`metadata_json`**: (JSON)

## Module: `auth`

### Model: `User`
- **`user_id`**: (Integer)
- **`username`**
- **`email`**
- **`password_hash`**
- **`user_role`**
- **`total_score`**: (Integer)
- **`last_seen`**
- **`timezone`**
- **`telegram_chat_id`**
- **`avatar_url`**
- **`last_preferences`**: (JSON)

### Model: `UserSession`
- **`user_id`**: (Integer)
- **`current_flashcard_container_id`**: (Integer)
- **`current_quiz_container_id`**: (Integer)
- **`current_course_container_id`**: (Integer)
- **`current_flashcard_mode`**
- **`current_quiz_mode`**
- **`current_quiz_batch_size`**: (Integer)
- **`flashcard_button_count`**: (Integer)
- **`last_updated`**

## Module: `collab`

### Model: `FlashcardCollabRoom`
- **`room_id`**: (Integer)
- **`room_code`**
- **`title`**
- **`host_user_id`**: (Integer)
- **`container_id`**: (Integer)
- **`mode`**
- **`button_count`**: (Integer)
- **`status`**
- **`is_public`**: (Boolean)
- **`created_at`**
- **`updated_at`**

### Model: `FlashcardCollabParticipant`
- **`participant_id`**: (Integer)
- **`room_id`**: (Integer)
- **`user_id`**: (Integer)
- **`is_host`**: (Boolean)
- **`status`**
- **`joined_at`**
- **`left_at`**

### Model: `FlashcardCollabMessage`
- **`message_id`**: (Integer)
- **`room_id`**: (Integer)
- **`user_id`**: (Integer)
- **`content`**: (Text)
- **`created_at`**

### Model: `FlashcardCollabRound`
- **`round_id`**: (Integer)
- **`room_id`**: (Integer)
- **`item_id`**: (Integer)
- **`status`**
- **`scheduled_for_user_id`**: (Integer)
- **`scheduled_due_at`**
- **`started_at`**
- **`completed_at`**

### Model: `FlashcardCollabAnswer`
- **`answer_id`**: (Integer)
- **`round_id`**: (Integer)
- **`user_id`**: (Integer)
- **`answer_label`**
- **`answer_quality`**: (Integer)
- **`created_at`**
- **`updated_at`**

### Model: `FlashcardRoomProgress`
- **`progress_id`**: (Integer)
- **`room_id`**: (Integer)
- **`item_id`**: (Integer)
- **`fsrs_state`**: (Integer)
- **`fsrs_due`**
- **`fsrs_stability`**: (Float)
- **`fsrs_difficulty`**: (Float)
- **`current_interval`**: (Float)
- **`repetitions`**: (Integer)
- **`lapses`**: (Integer)
- **`last_reviewed`**

### Model: `QuizBattleRoom`
- **`room_id`**: (Integer)
- **`room_code`**
- **`title`**
- **`host_user_id`**: (Integer)
- **`container_id`**: (Integer)
- **`status`**
- **`is_locked`**: (Boolean)
- **`max_players`**: (Integer)
- **`question_limit`**: (Integer)
- **`is_public`**: (Boolean)
- **`mode`**
- **`time_per_question_seconds`**: (Integer)
- **`question_order`**: (JSON)
- **`current_round_number`**: (Integer)
- **`created_at`**
- **`updated_at`**

### Model: `QuizBattleParticipant`
- **`participant_id`**: (Integer)
- **`room_id`**: (Integer)
- **`user_id`**: (Integer)
- **`is_host`**: (Boolean)
- **`status`**
- **`joined_at`**
- **`left_at`**
- **`kicked_by`**: (Integer)
- **`session_score`**: (Integer)
- **`correct_answers`**: (Integer)
- **`incorrect_answers`**: (Integer)

### Model: `QuizBattleRound`
- **`round_id`**: (Integer)
- **`room_id`**: (Integer)
- **`sequence_number`**: (Integer)
- **`item_id`**: (Integer)
- **`status`**
- **`started_at`**
- **`ended_at`**

### Model: `QuizBattleAnswer`
- **`answer_id`**: (Integer)
- **`round_id`**: (Integer)
- **`participant_id`**: (Integer)
- **`selected_option`**
- **`is_correct`**: (Boolean)
- **`score_delta`**: (Integer)
- **`correct_option`**
- **`explanation`**: (Text)
- **`answered_at`**

### Model: `QuizBattleMessage`
- **`message_id`**: (Integer)
- **`room_id`**: (Integer)
- **`user_id`**: (Integer)
- **`content`**: (Text)
- **`created_at`**

## Module: `content_generator`

### Model: `GenerationLog`
- **`id`**: (Integer)
- **`task_id`**
- **`request_type`**
- **`requester_module`**
- **`session_id`**
- **`session_name`**
- **`item_id`**: (Integer)
- **`item_title`**
- **`delay_seconds`**: (Integer)
- **`status`**
- **`stop_requested`**: (Boolean)
- **`input_payload`**: (Text)
- **`output_result`**: (Text)
- **`cost_tokens`**: (Integer)
- **`execution_time_ms`**: (Integer)
- **`error_message`**: (Text)
- **`created_at`**: (DateTime)
- **`completed_at`**: (DateTime)

## Module: `feedback`

### Model: `Feedback`
- **`feedback_id`**: (Integer)
- **`user_id`**: (Integer)
- **`type`**
- **`content`**: (Text)
- **`context_url`**
- **`status`**
- **`created_at`**
- **`resolved_at`**
- **`resolved_by_id`**: (Integer)
- **`meta_data`**: (JSON)

### Model: `FeedbackAttachment`
- **`attachment_id`**: (Integer)
- **`feedback_id`**: (Integer)
- **`file_path`**
- **`file_type`**
- **`created_at`**

## Module: `fsrs`

### Model: `ItemMemoryState`
- **`state_id`**: (Integer)
- **`user_id`**: (Integer)
- **`item_id`**: (Integer)
- **`stability`**: (Float)
- **`difficulty`**: (Float)
- **`state`**: (Integer)
- **`due_date`**
- **`last_review`**
- **`repetitions`**: (Integer)
- **`lapses`**: (Integer)
- **`streak`**: (Integer)
- **`incorrect_streak`**: (Integer)
- **`times_correct`**: (Integer)
- **`times_incorrect`**: (Integer)
- **`data`**: (JSON)
- **`created_at`**
- **`updated_at`**

## Module: `gamification`

### Model: `Badge`
- **`badge_id`**: (Integer)
- **`name`**
- **`description`**
- **`icon_class`**
- **`condition_type`**
- **`condition_value`**: (Integer)
- **`reward_points`**: (Integer)
- **`is_active`**: (Boolean)
- **`created_at`**

### Model: `UserBadge`
- **`id`**: (Integer)
- **`user_id`**: (Integer)
- **`badge_id`**: (Integer)
- **`earned_at`**

### Model: `ScoreLog`
- **`log_id`**: (Integer)
- **`user_id`**: (Integer)
- **`item_id`**: (Integer)
- **`score_change`**: (Integer)
- **`reason`**
- **`timestamp`**
- **`item_type`**

### Model: `Streak`
- **`user_id`**: (Integer)
- **`current_streak`**: (Integer)
- **`longest_streak`**: (Integer)
- **`last_activity_date`**: (Date)
- **`updated_at`**

## Module: `goals`

### Model: `Goal`
- **`goal_code`**
- **`title`**
- **`description`**: (Text)
- **`domain`**
- **`metric`**
- **`default_period`**
- **`default_target`**: (Integer)
- **`icon`**
- **`is_active`**: (Boolean)

### Model: `UserGoal`
- **`user_goal_id`**: (Integer)
- **`user_id`**: (Integer)
- **`goal_code`**
- **`target_value`**: (Integer)
- **`period`**
- **`scope`**
- **`reference_id`**: (Integer)
- **`start_date`**: (Date)
- **`end_date`**: (Date)
- **`is_active`**: (Boolean)
- **`created_at`**
- **`updated_at`**

### Model: `GoalProgress`
- **`progress_id`**: (Integer)
- **`user_goal_id`**: (Integer)
- **`date`**: (Date)
- **`current_value`**: (Integer)
- **`target_snapshot`**: (Integer)
- **`is_met`**: (Boolean)
- **`last_updated`**

## Module: `learning`

### Model: `LearningContainer`
- **`container_id`**: (Integer)
- **`creator_user_id`**: (Integer)
- **`container_type`**
- **`title`**
- **`description`**: (Text)
- **`cover_image`**
- **`tags`**
- **`is_public`**: (Boolean)
- **`created_at`**
- **`updated_at`**
- **`ai_prompt`**: (Text)
- **`ai_capabilities`**: (JSON)
- **`media_image_folder`**
- **`media_audio_folder`**
- **`settings`**: (JSON)

### Model: `LearningGroup`
- **`group_id`**: (Integer)
- **`container_id`**: (Integer)
- **`group_type`**
- **`content`**: (JSON)

### Model: `LearningItem`
- **`item_id`**: (Integer)
- **`container_id`**: (Integer)
- **`group_id`**: (Integer)
- **`item_type`**
- **`content`**: (JSON)
- **`order_in_container`**: (Integer)
- **`custom_data`**: (JSON)
- **`search_text`**: (Text)

### Model: `UserContainerState`
- **`id`**: (Integer)
- **`user_id`**: (Integer)
- **`container_id`**: (Integer)
- **`is_archived`**: (Boolean)
- **`is_favorite`**: (Boolean)
- **`last_accessed`**
- **`settings`**: (JSON)

### Model: `ContainerContributor`
- **`contributor_id`**: (Integer)
- **`container_id`**: (Integer)
- **`user_id`**: (Integer)
- **`permission_level`**
- **`granted_at`**

### Model: `UserItemMarker`
- **`marker_id`**: (Integer)
- **`user_id`**: (Integer)
- **`item_id`**: (Integer)
- **`marker_type`**
- **`created_at`**

### Model: `LearningProgress`
- **`progress_id`**: (Integer)
- **`user_id`**: (Integer)
- **`item_id`**: (Integer)
- **`learning_mode`**
- **`fsrs_stability`**: (Float)
- **`fsrs_difficulty`**: (Float)
- **`fsrs_state`**: (Integer)
- **`fsrs_due`**
- **`fsrs_last_review`**
- **`first_seen`**
- **`created_at`**
- **`updated_at`**
- **`lapses`**: (Integer)
- **`repetitions`**: (Integer)
- **`last_review_duration`**: (Integer)
- **`current_interval`**: (Float)
- **`times_correct`**: (Integer)
- **`times_incorrect`**: (Integer)
- **`correct_streak`**: (Integer)
- **`incorrect_streak`**: (Integer)
- **`mode_data`**: (JSON)

### Model: `LearningSession`
- **`session_id`**: (Integer)
- **`user_id`**: (Integer)
- **`learning_mode`**
- **`mode_config_id`**
- **`set_id_data`**: (JSON)
- **`status`**
- **`total_items`**: (Integer)
- **`correct_count`**: (Integer)
- **`incorrect_count`**: (Integer)
- **`vague_count`**: (Integer)
- **`points_earned`**: (Integer)
- **`processed_item_ids`**: (JSON)
- **`current_item_id`**: (Integer)
- **`session_data`**: (JSON)
- **`start_time`**
- **`last_activity`**
- **`end_time`**

## Module: `learning_history`

### Model: `StudyLog`
- **`log_id`**: (Integer)
- **`user_id`**: (Integer)
- **`item_id`**: (Integer)
- **`timestamp`**
- **`rating`**: (Integer)
- **`user_answer`**: (Text)
- **`is_correct`**: (Boolean)
- **`review_duration`**: (Integer)
- **`session_id`**: (Integer)
- **`container_id`**: (Integer)
- **`learning_mode`**
- **`fsrs_snapshot`**: (JSON)
- **`gamification_snapshot`**: (JSON)
- **`context_snapshot`**: (JSON)

## Module: `notes`

### Model: `Note`
- **`note_id`**: (Integer)
- **`user_id`**: (Integer)
- **`reference_type`**
- **`reference_id`**: (Integer)
- **`title`**
- **`content`**: (Text)
- **`created_at`**
- **`updated_at`**
- **`is_archived`**: (Boolean)
- **`tags`**

## Module: `notification`

### Model: `Notification`
- **`id`**: (Integer)
- **`user_id`**: (Integer)
- **`type`**
- **`title`**
- **`message`**: (Text)
- **`link`**
- **`is_read`**: (Boolean)
- **`created_at`**
- **`meta_data`**: (JSON)

### Model: `PushSubscription`
- **`id`**: (Integer)
- **`user_id`**: (Integer)
- **`endpoint`**
- **`auth_key`**
- **`p256dh_key`**
- **`created_at`**

### Model: `NotificationPreference`
- **`user_id`**: (Integer)
- **`email_enabled`**: (Boolean)
- **`push_enabled`**: (Boolean)
- **`study_reminders`**: (Boolean)
- **`achievement_updates`**: (Boolean)
- **`system_messages`**: (Boolean)
- **`marketing_updates`**: (Boolean)
- **`updated_at`**

## Module: `ops`

### Model: `BackgroundTask`
- **`task_id`**: (Integer)
- **`task_name`**
- **`status`**
- **`progress`**: (Integer)
- **`total`**: (Integer)
- **`message`**: (Text)
- **`stop_requested`**: (Boolean)
- **`is_enabled`**: (Boolean)
- **`last_updated`**

### Model: `BackgroundTaskLog`
- **`log_id`**: (Integer)
- **`task_id`**: (Integer)
- **`task_name`**
- **`status`**
- **`progress`**: (Integer)
- **`total`**: (Integer)
- **`message`**: (Text)
- **`stop_requested`**: (Boolean)
- **`created_at`**

## Module: `stats`

### Model: `UserMetric`
- **`user_id`**: (Integer)
- **`metric_key`**
- **`metric_value`**: (Float)
- **`updated_at`**

### Model: `DailyStat`
- **`stat_id`**: (Integer)
- **`user_id`**: (Integer)
- **`date`**: (Date)
- **`metric_key`**
- **`metric_value`**: (Float)
- **`updated_at`**

### Model: `Achievement`
- **`achievement_id`**: (Integer)
- **`user_id`**: (Integer)
- **`achievement_code`**
- **`achieved_at`**
- **`data`**: (JSON)

## Module: `translator`

### Model: `TranslationHistory`
- **`id`**: (Integer)
- **`user_id`**: (Integer)
- **`original_text`**: (Text)
- **`translated_text`**: (Text)
- **`source_lang`**
- **`target_lang`**
- **`created_at`**: (DateTime)

---
*Note: Bảng này được sinh tự động. Có thể không đầy đủ kiểu dữ liệu phức tạp hoặc Relationship (FK).*