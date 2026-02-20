# Cấu trúc Dự án MindStack

Tài liệu này mô tả cấu trúc thư mục tự động được sinh ra của dự án MindStack.

## 1. Cấu trúc Tổng quan (`newmindstack/`)

```text
newmindstack/
├── .agent/
│   └── workflows/
│       └── ai-guidelines.md
├── README.md
├── check_results.txt
├── database/
│   └── system_upgrade_state.json
├── docs/
│   ├── MODULE_REFACTOR_CHECKLIST.md
│   ├── MODULE_STRUCTURE.md
│   ├── database_schema.md
│   ├── features/
│   │   ├── VOCAB_MCQ.md
│   │   └── vocab_flashcard.md
│   ├── module_dependencies/
│   │   ├── AI.md
│   │   ├── access_control.md
│   │   ├── admin.md
│   │   ├── audio.md
│   │   ├── auth.md
│   │   ├── backup.md
│   │   ├── chat.md
│   │   ├── collab.md
│   │   ├── content_generator.md
│   │   ├── content_management.md
│   │   ├── course.md
│   │   ├── dashboard.md
│   │   ├── feedback.md
│   │   ├── fsrs.md
│   │   ├── gamification.md
│   │   ├── goals.md
│   │   ├── landing.md
│   │   ├── learning.md
│   │   ├── learning_history.md
│   │   ├── maintenance.md
│   │   ├── media.md
│   │   ├── notes.md
│   │   ├── notification.md
│   │   ├── ops.md
│   │   ├── quiz.md
│   │   ├── scoring.md
│   │   ├── session.md
│   │   ├── stats.md
│   │   ├── telegram_bot.md
│   │   ├── translator.md
│   │   ├── user_management.md
│   │   ├── user_profile.md
│   │   └── vocabulary.md
│   └── project_structure.md
├── mindstack_app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── bootstrap.py
│   │   ├── config.py
│   │   ├── defaults.py
│   │   ├── error_handlers.py
│   │   ├── extensions.py
│   │   ├── gamification_seeds.py
│   │   ├── logging_config.py
│   │   ├── maintenance.py
│   │   ├── module_registry.py
│   │   ├── services/
│   │   └── signals.py
│   ├── debug_stats_simple.py
│   ├── logics/
│   │   ├── __init__.py
│   │   └── config_parser.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── app_settings.py
│   ├── modules/
│   │   ├── AI/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── engines/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── gemini_client.py
│   │   │   │   ├── huggingface_client.py
│   │   │   │   └── hybrid_client.py
│   │   │   ├── events.py
│   │   │   ├── forms.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── prompt_manager.py
│   │   │   │   ├── prompts.py
│   │   │   │   └── response_parser.py
│   │   │   ├── models.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   ├── schemas.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── ai_gateway.py
│   │   │       ├── ai_manager.py
│   │   │       ├── ai_service.py
│   │   │       ├── autogen_service.py
│   │   │       ├── explanation_service.py
│   │   │       └── resource_manager.py
│   │   ├── __init__.py
│   │   ├── access_control/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── decorators.py
│   │   │   ├── events.py
│   │   │   ├── exceptions.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   │   └── policies.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   ├── schemas.py
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   └── permission_service.py
│   │   │   └── signals.py
│   │   ├── admin/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── context_processors.py
│   │   │   ├── forms.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   ├── schemas.py
│   │   │   └── services/
│   │   │       ├── media_service.py
│   │   │       └── settings_service.py
│   │   ├── audio/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── engines/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── edge.py
│   │   │   │   └── gtts_engine.py
│   │   │   ├── events.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   │   ├── audio_logic.py
│   │   │   │   ├── voice_engine.py
│   │   │   │   └── voice_parser.py
│   │   │   ├── models.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   ├── schemas.py
│   │   │   └── services/
│   │   │       └── audio_service.py
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── forms.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   ├── models.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   ├── schemas.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       └── auth_service.py
│   │   ├── backup/
│   │   │   ├── __init__.py
│   │   │   ├── events.py
│   │   │   ├── logics/
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   └── views.py
│   │   │   └── services/
│   │   │       ├── auto_backup_service.py
│   │   │       └── backup_service.py
│   │   ├── chat/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   └── api.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       └── chat_service.py
│   │   ├── collab/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── interface.py
│   │   │   ├── models.py
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       └── views.py
│   │   ├── content_generator/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── engine/
│   │   │   │   ├── __init__.py
│   │   │   │   └── core.py
│   │   │   ├── events.py
│   │   │   ├── exceptions.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   │   └── __init__.py
│   │   │   ├── models.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   ├── schemas.py
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   └── generator_service.py
│   │   │   ├── signals.py
│   │   │   └── tasks.py
│   │   ├── content_management/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── engine/
│   │   │   │   └── excel_exporter.py
│   │   │   ├── forms.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── parsers.py
│   │   │   │   └── validators.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   ├── flashcards.py
│   │   │   │   ├── media.py
│   │   │   │   └── views.py
│   │   │   ├── schemas.py
│   │   │   ├── services/
│   │   │   │   ├── kernel_service.py
│   │   │   │   └── management_service.py
│   │   │   └── signals.py
│   │   ├── course/
│   │   │   ├── __init__.py
│   │   │   ├── logics/
│   │   │   │   └── algorithms.py
│   │   │   ├── models.py
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       └── views.py
│   │   ├── dashboard/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   └── views.py
│   │   │   ├── schemas.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       └── dashboard_service.py
│   │   ├── feedback/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   ├── models.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   ├── schemas.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       └── feedback_service.py
│   │   ├── fsrs/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── engine/
│   │   │   │   ├── core.py
│   │   │   │   └── processor.py
│   │   │   ├── events.py
│   │   │   ├── exceptions.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   │   └── fsrs_engine.py
│   │   │   ├── models.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── admin_views.py
│   │   │   │   └── api.py
│   │   │   ├── schemas.py
│   │   │   ├── services/
│   │   │   │   ├── hard_item_service.py
│   │   │   │   ├── optimizer_service.py
│   │   │   │   ├── scheduler_service.py
│   │   │   │   └── settings_service.py
│   │   │   └── signals.py
│   │   ├── gamification/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── events.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   │   ├── __init__.py
│   │   │   │   └── streak_logic.py
│   │   │   ├── models.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   └── views.py
│   │   │   ├── schemas.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── badges_service.py
│   │   │       ├── gamification_kernel.py
│   │   │       ├── reward_manager.py
│   │   │       ├── scoring_service.py
│   │   │       └── streak_service.py
│   │   ├── goals/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── constants.py
│   │   │   ├── forms.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   │   ├── __init__.py
│   │   │   │   └── calculation.py
│   │   │   ├── models.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   └── views.py
│   │   │   ├── schemas.py
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── goal_kernel_service.py
│   │   │   │   └── goal_orchestrator.py
│   │   │   └── view_helpers.py
│   │   ├── landing/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── interface.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   └── views.py
│   │   │   └── schemas.py
│   │   ├── learning/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── marker.py
│   │   │   │   ├── marker_logic.py
│   │   │   │   └── scoring_engine.py
│   │   │   ├── models.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── daily_stats_service.py
│   │   │       ├── learning_metrics_service.py
│   │   │       ├── progress_service.py
│   │   │       ├── score_service.py
│   │   │       └── settings_service.py
│   │   ├── learning_history/
│   │   │   ├── __init__.py
│   │   │   ├── interface.py
│   │   │   ├── models.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── history_query_service.py
│   │   │       └── history_recorder.py
│   │   ├── maintenance/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── events.py
│   │   │   ├── middleware.py
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       └── views.py
│   │   ├── media/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── interface.py
│   │   │   ├── schemas.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       └── image_service.py
│   │   ├── notes/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── forms.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   │   └── content_processor.py
│   │   │   ├── models.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   ├── schemas.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── note_kernel.py
│   │   │       └── note_manager.py
│   │   ├── notification/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── events.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   ├── models.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   └── api.py
│   │   │   ├── schemas.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── delivery_service.py
│   │   │       ├── notification_manager.py
│   │   │       └── notification_service.py
│   │   ├── ops/
│   │   │   ├── __init__.py
│   │   │   ├── events.py
│   │   │   ├── interface.py
│   │   │   ├── models.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   └── services/
│   │   │       ├── reset_service.py
│   │   │       └── system_service.py
│   │   ├── quiz/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── engine/
│   │   │   │   └── core.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── algorithms.py
│   │   │   │   ├── quiz_logic.py
│   │   │   │   ├── session_logic.py
│   │   │   │   └── stats_logic.py
│   │   │   ├── models.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── battle.py
│   │   │   │   ├── individual_api.py
│   │   │   │   └── individual_views.py
│   │   │   ├── schemas.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── audio_service.py
│   │   │       ├── battle_service.py
│   │   │       └── quiz_config_service.py
│   │   ├── scoring/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── events.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   │   └── calculator.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   └── services/
│   │   │       └── scoring_config_service.py
│   │   ├── session/
│   │   │   ├── __init__.py
│   │   │   ├── drivers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   └── registry.py
│   │   │   ├── engine/
│   │   │   ├── interface.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── admin.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       └── session_service.py
│   │   ├── stats/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── chart_utils.py
│   │   │   │   └── time_logic.py
│   │   │   ├── models.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   ├── schemas.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── analytics_listener.py
│   │   │       ├── analytics_service.py
│   │   │       ├── leaderboard_service.py
│   │   │       ├── metrics.py
│   │   │       ├── metrics_kernel.py
│   │   │       ├── stats_aggregator.py
│   │   │       └── vocabulary_stats_service.py
│   │   ├── telegram_bot/
│   │   │   ├── __init__.py
│   │   │   ├── interface.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   └── api.py
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   └── bot_service.py
│   │   │   └── tasks.py
│   │   ├── translator/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── interface.py
│   │   │   ├── logics/
│   │   │   ├── models.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   ├── schemas.py
│   │   │   ├── services/
│   │   │   ├── services.py
│   │   │   └── static/
│   │   │       └── js/
│   │   ├── user_management/
│   │   │   ├── __init__.py
│   │   │   ├── interface.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   ├── schemas.py
│   │   │   └── services/
│   │   │       └── user_service.py
│   │   ├── user_profile/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── logics/
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py
│   │   │   │   └── views.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       └── profile_service.py
│   │   └── vocabulary/
│   │       ├── __init__.py
│   │       ├── config.py
│   │       ├── driver.py
│   │       ├── flashcard/
│   │       │   ├── __init__.py
│   │       │   ├── config.py
│   │       │   ├── engine/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── algorithms.py
│   │       │   │   ├── config.py
│   │       │   │   ├── core.py
│   │       │   │   ├── renderer.py
│   │       │   │   └── vocab_flashcard_mode.py
│   │       │   ├── events.py
│   │       │   ├── interface.py
│   │       │   ├── models.py
│   │       │   ├── routes/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── api.py
│   │       │   │   └── views.py
│   │       │   ├── schemas.py
│   │       │   ├── services/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── card_presenter.py
│   │       │   │   ├── flashcard_config_service.py
│   │       │   │   ├── flashcard_service.py
│   │       │   │   ├── item_service.py
│   │       │   │   ├── permission_service.py
│   │       │   │   └── query_builder.py
│   │       │   └── signals.py
│   │       ├── interface.py
│   │       ├── listening/
│   │       │   ├── __init__.py
│   │       │   ├── logics/
│   │       │   │   └── listening_logic.py
│   │       │   └── routes/
│   │       │       ├── __init__.py
│   │       │       └── views.py
│   │       ├── logics/
│   │       │   ├── cover_logic.py
│   │       │   └── flashcard_modes.py
│   │       ├── matching/
│   │       │   ├── __init__.py
│   │       │   ├── logics/
│   │       │   │   └── matching_logic.py
│   │       │   └── routes/
│   │       │       ├── __init__.py
│   │       │       └── views.py
│   │       ├── mcq/
│   │       │   ├── __init__.py
│   │       │   ├── engine/
│   │       │   │   ├── mcq_engine.py
│   │       │   │   └── selector.py
│   │       │   ├── interface.py
│   │       │   ├── logics/
│   │       │   │   ├── __init__.py
│   │       │   │   └── algorithms.py
│   │       │   ├── routes/
│   │       │   │   ├── __init__.py
│   │       │   │   └── views.py
│   │       │   └── services/
│   │       │       ├── __init__.py
│   │       │       ├── mcq_service.py
│   │       │       └── mcq_session_manager.py
│   │       ├── modes/
│   │       │   ├── __init__.py
│   │       │   ├── base_mode.py
│   │       │   ├── factory.py
│   │       │   ├── flashcard_mode.py
│   │       │   ├── listening_mode.py
│   │       │   ├── matching_mode.py
│   │       │   ├── mcq_mode.py
│   │       │   ├── speed_mode.py
│   │       │   └── typing_mode.py
│   │       ├── routes/
│   │       │   ├── __init__.py
│   │       │   ├── api.py
│   │       │   └── views.py
│   │       ├── schemas.py
│   │       ├── services/
│   │       │   ├── stats_container.py
│   │       │   ├── stats_session.py
│   │       │   └── vocabulary_service.py
│   │       ├── speed/
│   │       │   ├── __init__.py
│   │       │   └── routes/
│   │       │       ├── __init__.py
│   │       │       └── views.py
│   │       └── typing/
│   │           ├── __init__.py
│   │           ├── engine/
│   │           │   └── typing_engine.py
│   │           ├── interface.py
│   │           ├── logics/
│   │           │   └── algorithms.py
│   │           ├── routes/
│   │           │   ├── __init__.py
│   │           │   └── views.py
│   │           └── services/
│   │               ├── typing_service.py
│   │               └── typing_session_manager.py
│   ├── schemas.py
│   ├── services/
│   │   ├── config_service.py
│   │   ├── container_config_service.py
│   │   └── template_service.py
│   ├── themes/
│   │   ├── __init__.py
│   │   ├── admin/
│   │   │   ├── __init__.py
│   │   │   ├── static/
│   │   │   │   ├── ai/
│   │   │   │   │   └── js/
│   │   │   │   └── js/
│   │   │   └── templates/
│   │   │       ├── admin/
│   │   │       │   └── modules/
│   │   │       │       ├── AI/
│   │   │       │       │   └── api_keys/
│   │   │       │       │       ├── add_edit_api_key.html
│   │   │       │       │       └── api_keys.html
│   │   │       │       ├── access_control/
│   │   │       │       │   └── index.html
│   │   │       │       ├── admin/
│   │   │       │       │   ├── _voice_tasks_table.html
│   │   │       │       │   ├── admin_gamification/
│   │   │       │       │   │   ├── _tabs.html
│   │   │       │       │   │   ├── badge_form.html
│   │   │       │       │   │   ├── badges_list.html
│   │   │       │       │   │   └── points_settings.html
│   │   │       │       │   ├── admin_layout.html
│   │   │       │       │   ├── background_task_logs.html
│   │   │       │       │   ├── background_tasks.html
│   │   │       │       │   ├── content/
│   │   │       │       │   │   ├── dashboard.html
│   │   │       │       │   │   ├── edit.html
│   │   │       │       │   │   └── list.html
│   │   │       │       │   ├── content_config.html
│   │   │       │       │   ├── content_management.html
│   │   │       │       │   ├── dashboard.html
│   │   │       │       │   ├── includes/
│   │   │       │       │   │   └── _modal.html
│   │   │       │       │   ├── login.html
│   │   │       │       │   ├── maintenance/
│   │   │       │       │   │   └── index.html
│   │   │       │       │   ├── manage_modules.html
│   │   │       │       │   ├── manage_templates.html
│   │   │       │       │   ├── media_library.html
│   │   │       │       │   ├── ops/
│   │   │       │       │   │   ├── reset.html
│   │   │       │       │   │   └── upgrade.html
│   │   │       │       │   ├── scoring/
│   │   │       │       │   │   └── index.html
│   │   │       │       │   ├── sys_backup_manager.html
│   │   │       │       │   ├── system_settings.html
│   │   │       │       │   └── users/
│   │   │       │       │       ├── add_edit_user.html
│   │   │       │       │       └── users.html
│   │   │       │       ├── audio/
│   │   │       │       │   └── audio_studio.html
│   │   │       │       ├── fsrs/
│   │   │       │       │   └── fsrs_config.html
│   │   │       │       └── session/
│   │   │       │           └── admin_manage.html
│   │   │       └── modules/
│   │   │           └── content_generator/
│   │   │               ├── factory.html
│   │   │               ├── index.html
│   │   │               └── test.html
│   │   └── aura_mobile/
│   │       ├── __init__.py
│   │       ├── static/
│   │       │   ├── aura_mobile/
│   │       │   ├── img/
│   │       │   ├── js/
│   │       │   │   ├── notification/
│   │       │   │   └── utils/
│   │       │   ├── quiz/
│   │       │   │   └── css/
│   │       │   ├── vocab_flashcard/
│   │       │   │   ├── css/
│   │       │   │   └── js/
│   │       │   ├── vocab_listening/
│   │       │   │   └── js/
│   │       │   ├── vocab_matching/
│   │       │   │   └── js/
│   │       │   ├── vocab_speed/
│   │       │   │   └── js/
│   │       │   ├── vocab_typing/
│   │       │   │   └── js/
│   │       │   └── vocabulary/
│   │       │       ├── css/
│   │       │       └── js/
│   │       └── templates/
│   │           ├── aura_mobile/
│   │           │   ├── components/
│   │           │   │   ├── _app_logic.html
│   │           │   │   ├── _bottom_nav.html
│   │           │   │   ├── _confirmation_modal.html
│   │           │   │   ├── _global_styles.html
│   │           │   │   ├── _header.html
│   │           │   │   ├── _image_viewer.html
│   │           │   │   ├── _markdown_assets.html
│   │           │   │   ├── _memory_power.html
│   │           │   │   ├── _modal.html
│   │           │   │   ├── _navbar.html
│   │           │   │   ├── _score_toast.html
│   │           │   │   ├── _settings_modal.html
│   │           │   │   ├── ai_services/
│   │           │   │   │   └── _ai_modal.html
│   │           │   │   ├── chat/
│   │           │   │   │   └── chat_widget.html
│   │           │   │   ├── components/
│   │           │   │   │   ├── _mobile_footer.html
│   │           │   │   │   ├── _mobile_header.html
│   │           │   │   │   ├── dashboard_header.html
│   │           │   │   │   └── learning_header.html
│   │           │   │   ├── macros/
│   │           │   │   │   └── _ai_helpers.html
│   │           │   │   ├── navbar/
│   │           │   │   │   └── _session_header.html
│   │           │   │   ├── pagination/
│   │           │   │   │   ├── _pagination.html
│   │           │   │   │   └── _pagination_mobile.html
│   │           │   │   └── search/
│   │           │   │       ├── _search_compact.html
│   │           │   │       ├── _search_form.html
│   │           │   │       └── _search_form_mobile.html
│   │           │   ├── layouts/
│   │           │   │   └── base.html
│   │           │   └── modules/
│   │           │       ├── analytics/
│   │           │       │   ├── _leaderboard_list.html
│   │           │       │   ├── dashboard.html
│   │           │       │   ├── gamification/
│   │           │       │   │   ├── leaderboard.html
│   │           │       │   │   └── score_history.html
│   │           │       │   └── memory/
│   │           │       │       ├── components/
│   │           │       │       │   ├── _chart_lib.html
│   │           │       │       │   ├── _container_modal.html
│   │           │       │       │   ├── _item_charts.html
│   │           │       │       │   └── _stats_button.html
│   │           │       │       └── dashboard/
│   │           │       │           └── default/
│   │           │       │               └── index.html
│   │           │       ├── auth/
│   │           │       │   ├── login/
│   │           │       │   │   └── login.html
│   │           │       │   └── register/
│   │           │       │       └── register.html
│   │           │       ├── content_management/
│   │           │       │   ├── _index_desktop.html
│   │           │       │   ├── _index_mobile.html
│   │           │       │   ├── courses/
│   │           │       │   │   ├── excel/
│   │           │       │   │   │   └── manage_course_excel.html
│   │           │       │   │   ├── lessons/
│   │           │       │   │   │   ├── add_edit_lesson.html
│   │           │       │   │   │   └── lessons.html
│   │           │       │   │   └── sets/
│   │           │       │   │       ├── _add_edit_course_set_bare.html
│   │           │       │   │       ├── _courses_list.html
│   │           │       │   │       ├── add_edit_course_set.html
│   │           │       │   │       └── courses.html
│   │           │       │   ├── flashcards/
│   │           │       │   │   ├── excel/
│   │           │       │   │   │   └── manage_flashcard_excel.html
│   │           │       │   │   ├── items/
│   │           │       │   │   │   ├── _add_edit_flashcard_item_bare.html
│   │           │       │   │   │   ├── _flashcard_items_list_desktop.html
│   │           │       │   │   │   ├── _flashcard_items_list_mobile.html
│   │           │       │   │   │   ├── add_edit_flashcard_item.html
│   │           │       │   │   │   └── flashcard_items.html
│   │           │       │   │   ├── sets/
│   │           │       │   │   │   ├── _add_edit_flashcard_set_bare.html
│   │           │       │   │   │   ├── _flashcard_sets_list.html
│   │           │       │   │   │   ├── add_edit_flashcard_set.html
│   │           │       │   │   │   └── flashcard_sets.html
│   │           │       │   │   └── shared/
│   │           │       │   │       ├── _flashcard_audio_control_scripts.html
│   │           │       │   │       └── _flashcard_image_control_scripts.html
│   │           │       │   ├── index.html
│   │           │       │   ├── manage_contributors.html
│   │           │       │   ├── quizzes/
│   │           │       │   │   ├── excel/
│   │           │       │   │   │   └── manage_quiz_excel.html
│   │           │       │   │   ├── items/
│   │           │       │   │   │   ├── _add_edit_quiz_item_bare.html
│   │           │       │   │   │   ├── _quiz_items_list.html
│   │           │       │   │   │   ├── add_edit_quiz_item.html
│   │           │       │   │   │   └── quiz_items.html
│   │           │       │   │   ├── sets/
│   │           │       │   │   │   ├── _add_edit_quiz_set_bare.html
│   │           │       │   │   │   ├── _quiz_sets_list.html
│   │           │       │   │   │   ├── add_edit_quiz_set.html
│   │           │       │   │   │   └── quiz_sets.html
│   │           │       │   │   └── shared/
│   │           │       │   │       └── _quiz_media_scripts.html
│   │           │       │   └── shared/
│   │           │       │       ├── _cover_preview_script.html
│   │           │       │       └── _shared_styles.html
│   │           │       ├── dashboard/
│   │           │       │   └── index.html
│   │           │       ├── feedback/
│   │           │       │   ├── _feedback_modal.html
│   │           │       │   ├── _feedback_table.html
│   │           │       │   ├── _general_feedback_modal.html
│   │           │       │   └── manage_feedback.html
│   │           │       ├── goals/
│   │           │       │   ├── edit.html
│   │           │       │   └── manage.html
│   │           │       ├── landing/
│   │           │       │   └── index.html
│   │           │       ├── learning/
│   │           │       │   ├── collab/
│   │           │       │   │   ├── default/
│   │           │       │   │   │   └── dashboard.html
│   │           │       │   │   └── flashcard/
│   │           │       │   │       ├── _modes_list.html
│   │           │       │   │       ├── _sets_list.html
│   │           │       │   │       ├── index.html
│   │           │       │   │       └── room/
│   │           │       │   │           └── index.html
│   │           │       │   ├── course/
│   │           │       │   │   ├── _base.html
│   │           │       │   │   ├── _course_sets_selection.html
│   │           │       │   │   ├── _lesson_selection.html
│   │           │       │   │   ├── course_learning_dashboard.html
│   │           │       │   │   ├── course_session.html
│   │           │       │   │   └── default/
│   │           │       │   │       ├── _course_sets_selection.html
│   │           │       │   │       ├── _lesson_selection.html
│   │           │       │   │       ├── course_learning_dashboard.html
│   │           │       │   │       └── course_session.html
│   │           │       │   ├── modals/
│   │           │       │   │   └── log_detail.html
│   │           │       │   ├── practice/
│   │           │       │   │   ├── default/
│   │           │       │   │   │   ├── dashboard.html
│   │           │       │   │   │   ├── hub.html
│   │           │       │   │   │   ├── quiz_dashboard.html
│   │           │       │   │   │   └── setup.html
│   │           │       │   │   └── flashcard/
│   │           │       │   │       ├── dashboard.html
│   │           │       │   │       └── setup.html
│   │           │       │   ├── quiz/
│   │           │       │   │   ├── battle/
│   │           │       │   │   │   ├── index.html
│   │           │       │   │   │   └── room/
│   │           │       │   │   │       └── index.html
│   │           │       │   │   ├── dashboard/
│   │           │       │   │   │   ├── css/
│   │           │       │   │   │   ├── index.html
│   │           │       │   │   │   └── js/
│   │           │       │   │   ├── individual/
│   │           │       │   │   │   ├── session/
│   │           │       │   │   │   │   ├── _base.html
│   │           │       │   │   │   │   └── index.html
│   │           │       │   │   │   ├── setup/
│   │           │       │   │   │   │   ├── default/
│   │           │       │   │   │   │   │   ├── _modes_list.html
│   │           │       │   │   │   │   │   ├── _quiz_custom_options.html
│   │           │       │   │   │   │   │   ├── _quiz_modes_selection_mobile.html
│   │           │       │   │   │   │   │   └── _sets_list.html
│   │           │       │   │   │   │   └── index.html
│   │           │       │   │   │   └── static/
│   │           │       │   │   │       └── css/
│   │           │       │   │   └── stats/
│   │           │       │   │       ├── _item_stats_content.html
│   │           │       │   │       └── _modal_stats.html
│   │           │       │   ├── session_summary.html
│   │           │       │   ├── sessions.html
│   │           │       │   ├── vocab_listening/
│   │           │       │   │   ├── session/
│   │           │       │   │   │   └── index.html
│   │           │       │   │   └── setup/
│   │           │       │   │       ├── default/
│   │           │       │   │       │   └── index.html
│   │           │       │   │       └── index.html
│   │           │       │   ├── vocab_matching/
│   │           │       │   │   └── session/
│   │           │       │   │       └── index.html
│   │           │       │   ├── vocab_mcq/
│   │           │       │   │   ├── session/
│   │           │       │   │   │   └── index.html
│   │           │       │   │   └── setup/
│   │           │       │   │       └── index.html
│   │           │       │   ├── vocab_speed/
│   │           │       │   │   ├── session/
│   │           │       │   │   │   └── index.html
│   │           │       │   │   └── setup/
│   │           │       │   │       └── index.html
│   │           │       │   ├── vocab_typing/
│   │           │       │   │   ├── session/
│   │           │       │   │   │   └── index.html
│   │           │       │   │   └── setup/
│   │           │       │   │       └── index.html
│   │           │       │   └── vocabulary/
│   │           │       ├── notes/
│   │           │       │   ├── _note_panel.html
│   │           │       │   └── manage_notes.html
│   │           │       ├── notification/
│   │           │       │   └── center.html
│   │           │       ├── session/
│   │           │       ├── stats/
│   │           │       │   └── index.html
│   │           │       ├── system/
│   │           │       │   └── maintenance.html
│   │           │       ├── test.html
│   │           │       ├── translator/
│   │           │       │   └── history.html
│   │           │       ├── user_profile/
│   │           │       │   ├── _base.html
│   │           │       │   ├── change_password.html
│   │           │       │   ├── edit_profile.html
│   │           │       │   └── profile.html
│   │           │       ├── vocab_flashcard/
│   │           │       │   ├── _modes_list.html
│   │           │       │   ├── _sets_list.html
│   │           │       │   ├── components/
│   │           │       │   │   └── card.html
│   │           │       │   ├── partials/
│   │           │       │   │   ├── card_back.html
│   │           │       │   │   ├── card_front.html
│   │           │       │   │   └── toolbar.html
│   │           │       │   ├── session.html
│   │           │       │   ├── setup.html
│   │           │       │   └── summary.html
│   │           │       └── vocabulary/
│   │           │           ├── dashboard/
│   │           │           │   ├── _container_stats_modal.html
│   │           │           │   ├── _inject_stats_button.html
│   │           │           │   ├── _item_stats_charts.html
│   │           │           │   ├── _stats_enhancement.html
│   │           │           │   ├── components/
│   │           │           │   │   ├── modals/
│   │           │           │   │   │   ├── _container_stats_modal.html
│   │           │           │   │   │   ├── _edit_set_modal.html
│   │           │           │   │   │   └── _settings_modal.html
│   │           │           │   │   ├── stats/
│   │           │           │   │   │   ├── _inject_stats_button.html
│   │           │           │   │   │   ├── _item_stats_charts.html
│   │           │           │   │   │   └── _stats_enhancement.html
│   │           │           │   │   └── steps/
│   │           │           │   │       ├── _flashcard_options.html
│   │           │           │   │       ├── _mcq_options.html
│   │           │           │   │       └── _modes.html
│   │           │           │   ├── css/
│   │           │           │   ├── detail.html
│   │           │           │   ├── index.html
│   │           │           │   └── js/
│   │           │           ├── detail/
│   │           │           │   ├── _modal_stats.html
│   │           │           │   ├── _vocab_detail_content.html
│   │           │           │   ├── vocab_detail.html
│   │           │           │   └── vocab_detail_modal.html
│   │           │           ├── flashcard/
│   │           │           │   ├── components/
│   │           │           │   │   └── _memory_power_widget.html
│   │           │           │   ├── session/
│   │           │           │   │   └── index.html
│   │           │           │   └── setup/
│   │           │           │       └── index.html
│   │           │           └── modes/
│   │           │               └── index.html
│   │           └── maintenance/
│   │               └── maintenance.html
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── bbcode_parser.py
│   │   ├── content_renderer.py
│   │   ├── db_session.py
│   │   ├── excel.py
│   │   ├── html_sanitizer.py
│   │   ├── media_paths.py
│   │   ├── pagination.py
│   │   ├── search.py
│   │   ├── template_filters.py
│   │   ├── template_helpers.py
│   │   └── time_utils.py
│   └── vapid_keys.txt
├── requirements.txt
├── scripts/
│   ├── check_module_imports.py
│   ├── generate_module_docs.py
│   ├── generate_schema_docs.py
│   └── generate_structure_docs.py
└── start_mindstack_app.py
```

