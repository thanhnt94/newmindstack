# Cấu trúc Chi tiết Dự án MindStack

```text
newmindstack/
│   ├── .env
│   ├── .env.example
│   ├── .gitignore
│   ├── clear_ai.py
│   ├── debug_containers.py
│   ├── debug_output.txt
│   ├── debug_stats.py
│   ├── debug_urls.py
│   ├── README.md
│   ├── requirements.txt
│   ├── start_mindstack_app.py
│   ├── test_audio_gen.py
│   ├── docs/
│   │   ├── database_schema.md
│   │   ├── MODULE_REFACTOR_CHECKLIST.md
│   │   ├── module_relationships.md
│   │   ├── MODULE_STRUCTURE.md
│   │   ├── project_structure.md
│   │   ├── project_structure_full.md
│   ├── mindstack_app/
│   │   ├── debug_stats_simple.py
│   │   ├── schemas.py
│   │   ├── vapid_keys.txt
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── bootstrap.py
│   │   │   ├── config.py
│   │   │   ├── defaults.py
│   │   │   ├── error_handlers.py
│   │   │   ├── extensions.py
│   │   │   ├── gamification_seeds.py
│   │   │   ├── logging_config.py
│   │   │   ├── maintenance.py
│   │   │   ├── module_registry.py
│   │   │   ├── signals.py
│   │   │   ├── __init__.py
│   │   │   ├── services/
│   │   ├── logics/
│   │   │   ├── config_parser.py
│   │   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── app_settings.py
│   │   │   ├── __init__.py
│   │   ├── modules/
│   │   │   ├── __init__.py
│   │   │   ├── access_control/
│   │   │   │   ├── config.py
│   │   │   │   ├── decorators.py
│   │   │   │   ├── events.py
│   │   │   │   ├── exceptions.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── signals.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── policies.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── permission_service.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── tests/
│   │   │   │   │   ├── test_flows.py
│   │   │   ├── admin/
│   │   │   │   ├── config.py
│   │   │   │   ├── context_processors.py
│   │   │   │   ├── forms.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── media_service.py
│   │   │   │   │   ├── settings_service.py
│   │   │   ├── AI/
│   │   │   │   ├── config.py
│   │   │   │   ├── events.py
│   │   │   │   ├── forms.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── engines/
│   │   │   │   │   ├── gemini_client.py
│   │   │   │   │   ├── huggingface_client.py
│   │   │   │   │   ├── hybrid_client.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── prompts.py
│   │   │   │   │   ├── prompt_manager.py
│   │   │   │   │   ├── response_parser.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── ai_gateway.py
│   │   │   │   │   ├── ai_manager.py
│   │   │   │   │   ├── ai_service.py
│   │   │   │   │   ├── autogen_service.py
│   │   │   │   │   ├── explanation_service.py
│   │   │   │   │   ├── resource_manager.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── tests/
│   │   │   │   │   ├── test_autogen.py
│   │   │   ├── audio/
│   │   │   │   ├── config.py
│   │   │   │   ├── events.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── engines/
│   │   │   │   │   ├── base.py
│   │   │   │   │   ├── edge.py
│   │   │   │   │   ├── gtts_engine.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── audio_logic.py
│   │   │   │   │   ├── voice_engine.py
│   │   │   │   │   ├── voice_parser.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── audio_service.py
│   │   │   ├── auth/
│   │   │   │   ├── config.py
│   │   │   │   ├── forms.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── auth_service.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── backup/
│   │   │   │   ├── events.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   ├── routes/
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── auto_backup_service.py
│   │   │   │   │   ├── backup_service.py
│   │   │   ├── chat/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── chat_service.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── collab/
│   │   │   │   ├── config.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── README.md
│   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── content_generator/
│   │   │   │   ├── config.py
│   │   │   │   ├── events.py
│   │   │   │   ├── exceptions.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── signals.py
│   │   │   │   ├── tasks.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── engine/
│   │   │   │   │   ├── core.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── generator_service.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── tests/
│   │   │   ├── content_management/
│   │   │   │   ├── config.py
│   │   │   │   ├── forms.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── README.md
│   │   │   │   ├── schemas.py
│   │   │   │   ├── signals.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── engine/
│   │   │   │   │   ├── excel_exporter.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── parsers.py
│   │   │   │   │   ├── validators.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── flashcards.py
│   │   │   │   │   ├── media.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── kernel_service.py
│   │   │   │   │   ├── management_service.py
│   │   │   ├── course/
│   │   │   │   ├── models.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── algorithms.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── dashboard/
│   │   │   │   ├── config.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── README.md
│   │   │   │   ├── schemas.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   ├── routes/
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── dashboard_service.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── feedback/
│   │   │   │   ├── config.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── feedback_service.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── fsrs/
│   │   │   │   ├── config.py
│   │   │   │   ├── events.py
│   │   │   │   ├── exceptions.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── README.md
│   │   │   │   ├── schemas.py
│   │   │   │   ├── signals.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── engine/
│   │   │   │   │   ├── core.py
│   │   │   │   │   ├── processor.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── fsrs_engine.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── admin_views.py
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── hard_item_service.py
│   │   │   │   │   ├── optimizer_service.py
│   │   │   │   │   ├── scheduler_service.py
│   │   │   │   │   ├── settings_service.py
│   │   │   ├── gamification/
│   │   │   │   ├── config.py
│   │   │   │   ├── events.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── README.md
│   │   │   │   ├── schemas.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── streak_logic.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── badges_service.py
│   │   │   │   │   ├── gamification_kernel.py
│   │   │   │   │   ├── reward_manager.py
│   │   │   │   │   ├── scoring_service.py
│   │   │   │   │   ├── streak_service.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── goals/
│   │   │   │   ├── config.py
│   │   │   │   ├── constants.py
│   │   │   │   ├── forms.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── view_helpers.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── calculation.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── goal_kernel_service.py
│   │   │   │   │   ├── goal_orchestrator.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── landing/
│   │   │   │   ├── config.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── learning/
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── README.md
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── marker.py
│   │   │   │   │   ├── marker_logic.py
│   │   │   │   │   ├── scoring_engine.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── daily_stats_service.py
│   │   │   │   │   ├── learning_metrics_service.py
│   │   │   │   │   ├── progress_service.py
│   │   │   │   │   ├── score_service.py
│   │   │   │   │   ├── settings_service.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── learning_history/
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── history_query_service.py
│   │   │   │   │   ├── history_recorder.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── maintenance/
│   │   │   │   ├── config.py
│   │   │   │   ├── events.py
│   │   │   │   ├── middleware.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── media/
│   │   │   │   ├── config.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── image_service.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── notes/
│   │   │   │   ├── config.py
│   │   │   │   ├── forms.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── content_processor.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── note_kernel.py
│   │   │   │   │   ├── note_manager.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── notification/
│   │   │   │   ├── config.py
│   │   │   │   ├── events.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── delivery_service.py
│   │   │   │   │   ├── notification_manager.py
│   │   │   │   │   ├── notification_service.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── ops/
│   │   │   │   ├── events.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── reset_service.py
│   │   │   ├── quiz/
│   │   │   │   ├── config.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── README.md
│   │   │   │   ├── schemas.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── engine/
│   │   │   │   │   ├── core.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── algorithms.py
│   │   │   │   │   ├── quiz_logic.py
│   │   │   │   │   ├── session_logic.py
│   │   │   │   │   ├── stats_logic.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── battle.py
│   │   │   │   │   ├── individual_api.py
│   │   │   │   │   ├── individual_views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── audio_service.py
│   │   │   │   │   ├── battle_service.py
│   │   │   │   │   ├── quiz_config_service.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── scoring/
│   │   │   │   ├── config.py
│   │   │   │   ├── events.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── scoring_config_service.py
│   │   │   ├── session/
│   │   │   │   ├── interface.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── engine/
│   │   │   │   ├── routes/
│   │   │   │   │   ├── admin.py
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── session_service.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── stats/
│   │   │   │   ├── config.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── README.md
│   │   │   │   ├── schemas.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── chart_utils.py
│   │   │   │   │   ├── time_logic.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── analytics_listener.py
│   │   │   │   │   ├── analytics_service.py
│   │   │   │   │   ├── leaderboard_service.py
│   │   │   │   │   ├── metrics.py
│   │   │   │   │   ├── metrics_kernel.py
│   │   │   │   │   ├── stats_aggregator.py
│   │   │   │   │   ├── vocabulary_stats_service.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── telegram_bot/
│   │   │   │   ├── interface.py
│   │   │   │   ├── tasks.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── bot_service.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── translator/
│   │   │   │   ├── config.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── services.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   ├── static/
│   │   │   │   │   ├── js/
│   │   │   │   │   │   ├── translator.js
│   │   │   ├── user_management/
│   │   │   │   ├── interface.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── user_service.py
│   │   │   ├── user_profile/
│   │   │   │   ├── config.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── profile_service.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── vocabulary/
│   │   │   │   ├── config.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── cover_logic.py
│   │   │   │   │   ├── flashcard_modes.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── stats_container.py
│   │   │   │   │   ├── stats_session.py
│   │   │   │   │   ├── vocabulary_service.py
│   │   │   ├── vocab_flashcard/
│   │   │   │   ├── config.py
│   │   │   │   ├── events.py
│   │   │   │   ├── interface.py
│   │   │   │   ├── models.py
│   │   │   │   ├── README.md
│   │   │   │   ├── schemas.py
│   │   │   │   ├── signals.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── engine/
│   │   │   │   │   ├── algorithms.py
│   │   │   │   │   ├── config.py
│   │   │   │   │   ├── core.py
│   │   │   │   │   ├── vocab_flashcard_mode.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── api.py
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── card_presenter.py
│   │   │   │   │   ├── flashcard_config_service.py
│   │   │   │   │   ├── flashcard_service.py
│   │   │   │   │   ├── item_service.py
│   │   │   │   │   ├── permission_service.py
│   │   │   │   │   ├── query_builder.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── vocab_listening/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── listening_logic.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── vocab_matching/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── matching_logic.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── vocab_mcq/
│   │   │   │   ├── interface.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── engine/
│   │   │   │   │   ├── mcq_engine.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── algorithms.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── services/
│   │   │   │   │   ├── mcq_service.py
│   │   │   │   │   ├── mcq_session_manager.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── vocab_speed/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   │   ├── vocab_typing/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logics/
│   │   │   │   │   ├── typing_logic.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── views.py
│   │   │   │   │   ├── __init__.py
│   │   ├── services/
│   │   │   ├── config_service.py
│   │   │   ├── container_config_service.py
│   │   │   ├── template_service.py
│   │   ├── themes/
│   │   │   ├── __init__.py
│   │   │   ├── admin/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── static/
│   │   │   │   │   ├── ai/
│   │   │   │   │   │   ├── js/
│   │   │   │   │   │   │   ├── autogen.js
│   │   │   │   │   ├── js/
│   │   │   │   ├── templates/
│   │   │   │   │   ├── admin/
│   │   │   │   │   │   ├── modules/
│   │   │   │   │   │   │   ├── access_control/
│   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   ├── admin/
│   │   │   │   │   │   │   │   ├── admin_layout.html
│   │   │   │   │   │   │   │   ├── background_tasks.html
│   │   │   │   │   │   │   │   ├── background_task_logs.html
│   │   │   │   │   │   │   │   ├── content_config.html
│   │   │   │   │   │   │   │   ├── content_management.html
│   │   │   │   │   │   │   │   ├── dashboard.html
│   │   │   │   │   │   │   │   ├── login.html
│   │   │   │   │   │   │   │   ├── manage_modules.html
│   │   │   │   │   │   │   │   ├── manage_templates.html
│   │   │   │   │   │   │   │   ├── media_library.html
│   │   │   │   │   │   │   │   ├── system_settings.html
│   │   │   │   │   │   │   │   ├── sys_backup_manager.html
│   │   │   │   │   │   │   │   ├── _voice_tasks_table.html
│   │   │   │   │   │   │   │   ├── admin_gamification/
│   │   │   │   │   │   │   │   │   ├── badges_list.html
│   │   │   │   │   │   │   │   │   ├── badge_form.html
│   │   │   │   │   │   │   │   │   ├── points_settings.html
│   │   │   │   │   │   │   │   │   ├── _tabs.html
│   │   │   │   │   │   │   │   ├── content/
│   │   │   │   │   │   │   │   │   ├── dashboard.html
│   │   │   │   │   │   │   │   │   ├── edit.html
│   │   │   │   │   │   │   │   │   ├── list.html
│   │   │   │   │   │   │   │   ├── includes/
│   │   │   │   │   │   │   │   │   ├── _modal.html
│   │   │   │   │   │   │   │   ├── maintenance/
│   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   ├── ops/
│   │   │   │   │   │   │   │   │   ├── reset.html
│   │   │   │   │   │   │   │   ├── scoring/
│   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   ├── users/
│   │   │   │   │   │   │   │   │   ├── add_edit_user.html
│   │   │   │   │   │   │   │   │   ├── users.html
│   │   │   │   │   │   │   ├── AI/
│   │   │   │   │   │   │   │   ├── api_keys/
│   │   │   │   │   │   │   │   │   ├── add_edit_api_key.html
│   │   │   │   │   │   │   │   │   ├── api_keys.html
│   │   │   │   │   │   │   ├── audio/
│   │   │   │   │   │   │   │   ├── audio_studio.html
│   │   │   │   │   │   │   ├── fsrs/
│   │   │   │   │   │   │   │   ├── fsrs_config.html
│   │   │   │   │   │   │   ├── session/
│   │   │   │   │   │   │   │   ├── admin_manage.html
│   │   │   │   │   ├── modules/
│   │   │   │   │   │   ├── content_generator/
│   │   │   │   │   │   │   ├── factory.html
│   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   ├── test.html
│   │   │   ├── aura_mobile/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── static/
│   │   │   │   │   ├── aura_mobile/
│   │   │   │   │   ├── img/
│   │   │   │   │   │   ├── favicon.png
│   │   │   │   │   ├── js/
│   │   │   │   │   │   ├── cms.js
│   │   │   │   │   │   ├── notification/
│   │   │   │   │   │   │   ├── pro_sw.js
│   │   │   │   │   ├── quiz/
│   │   │   │   │   │   ├── css/
│   │   │   │   │   │   │   ├── session_batch.css
│   │   │   │   │   │   │   ├── session_single.css
│   │   │   │   │   ├── vocabulary/
│   │   │   │   │   │   ├── css/
│   │   │   │   │   │   │   ├── dashboard.css
│   │   │   │   │   │   │   ├── dashboard_detail.css
│   │   │   │   │   │   ├── js/
│   │   │   │   │   │   │   ├── dashboard_detail.js
│   │   │   │   │   ├── vocab_flashcard/
│   │   │   │   │   │   ├── css/
│   │   │   │   │   │   │   ├── session.css
│   │   │   │   │   │   ├── js/
│   │   │   │   │   │   │   ├── audio_manager.js
│   │   │   │   │   │   │   ├── flashcard_viewport.js
│   │   │   │   │   │   │   ├── index.js
│   │   │   │   │   │   │   ├── renderers.js
│   │   │   │   │   │   │   ├── render_card.js
│   │   │   │   │   │   │   ├── session_init.js
│   │   │   │   │   │   │   ├── session_manager.js
│   │   │   │   │   │   │   ├── session_ui.js
│   │   │   │   │   │   │   ├── ui_manager.js
│   │   │   │   │   │   │   ├── utils.js
│   │   │   │   ├── templates/
│   │   │   │   │   ├── aura_mobile/
│   │   │   │   │   │   ├── components/
│   │   │   │   │   │   │   ├── _app_logic.html
│   │   │   │   │   │   │   ├── _bottom_nav.html
│   │   │   │   │   │   │   ├── _confirmation_modal.html
│   │   │   │   │   │   │   ├── _global_styles.html
│   │   │   │   │   │   │   ├── _header.html
│   │   │   │   │   │   │   ├── _image_viewer.html
│   │   │   │   │   │   │   ├── _markdown_assets.html
│   │   │   │   │   │   │   ├── _memory_power.html
│   │   │   │   │   │   │   ├── _modal.html
│   │   │   │   │   │   │   ├── _navbar.html
│   │   │   │   │   │   │   ├── _score_toast.html
│   │   │   │   │   │   │   ├── _settings_modal.html
│   │   │   │   │   │   │   ├── ai_services/
│   │   │   │   │   │   │   │   ├── .keep
│   │   │   │   │   │   │   │   ├── _ai_modal.html
│   │   │   │   │   │   │   ├── chat/
│   │   │   │   │   │   │   │   ├── chat_widget.html
│   │   │   │   │   │   │   ├── components/
│   │   │   │   │   │   │   │   ├── dashboard_header.html
│   │   │   │   │   │   │   │   ├── learning_header.html
│   │   │   │   │   │   │   │   ├── _mobile_footer.html
│   │   │   │   │   │   │   │   ├── _mobile_header.html
│   │   │   │   │   │   │   ├── macros/
│   │   │   │   │   │   │   │   ├── _ai_helpers.html
│   │   │   │   │   │   │   ├── navbar/
│   │   │   │   │   │   │   │   ├── _session_header.html
│   │   │   │   │   │   │   ├── pagination/
│   │   │   │   │   │   │   │   ├── _pagination.html
│   │   │   │   │   │   │   │   ├── _pagination_mobile.html
│   │   │   │   │   │   │   ├── search/
│   │   │   │   │   │   │   │   ├── _search_compact.html
│   │   │   │   │   │   │   │   ├── _search_form.html
│   │   │   │   │   │   │   │   ├── _search_form_mobile.html
│   │   │   │   │   │   ├── layouts/
│   │   │   │   │   │   │   ├── base.html
│   │   │   │   │   │   ├── modules/
│   │   │   │   │   │   │   ├── test.html
│   │   │   │   │   │   │   ├── analytics/
│   │   │   │   │   │   │   │   ├── dashboard.html
│   │   │   │   │   │   │   │   ├── _leaderboard_list.html
│   │   │   │   │   │   │   │   ├── gamification/
│   │   │   │   │   │   │   │   │   ├── leaderboard.html
│   │   │   │   │   │   │   │   │   ├── score_history.html
│   │   │   │   │   │   │   │   ├── memory/
│   │   │   │   │   │   │   │   │   ├── components/
│   │   │   │   │   │   │   │   │   │   ├── _chart_lib.html
│   │   │   │   │   │   │   │   │   │   ├── _container_modal.html
│   │   │   │   │   │   │   │   │   │   ├── _item_charts.html
│   │   │   │   │   │   │   │   │   │   ├── _stats_button.html
│   │   │   │   │   │   │   │   │   ├── dashboard/
│   │   │   │   │   │   │   │   │   │   ├── default/
│   │   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   ├── auth/
│   │   │   │   │   │   │   │   ├── .keep
│   │   │   │   │   │   │   │   ├── login/
│   │   │   │   │   │   │   │   │   ├── login.html
│   │   │   │   │   │   │   │   ├── register/
│   │   │   │   │   │   │   │   │   ├── register.html
│   │   │   │   │   │   │   ├── content_management/
│   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   ├── manage_contributors.html
│   │   │   │   │   │   │   │   ├── _index_desktop.html
│   │   │   │   │   │   │   │   ├── _index_mobile.html
│   │   │   │   │   │   │   │   ├── courses/
│   │   │   │   │   │   │   │   │   ├── excel/
│   │   │   │   │   │   │   │   │   │   ├── manage_course_excel.html
│   │   │   │   │   │   │   │   │   ├── lessons/
│   │   │   │   │   │   │   │   │   │   ├── add_edit_lesson.html
│   │   │   │   │   │   │   │   │   │   ├── lessons.html
│   │   │   │   │   │   │   │   │   ├── sets/
│   │   │   │   │   │   │   │   │   │   ├── add_edit_course_set.html
│   │   │   │   │   │   │   │   │   │   ├── courses.html
│   │   │   │   │   │   │   │   │   │   ├── _add_edit_course_set_bare.html
│   │   │   │   │   │   │   │   │   │   ├── _courses_list.html
│   │   │   │   │   │   │   │   ├── flashcards/
│   │   │   │   │   │   │   │   │   ├── excel/
│   │   │   │   │   │   │   │   │   │   ├── manage_flashcard_excel.html
│   │   │   │   │   │   │   │   │   ├── items/
│   │   │   │   │   │   │   │   │   │   ├── add_edit_flashcard_item.html
│   │   │   │   │   │   │   │   │   │   ├── flashcard_items.html
│   │   │   │   │   │   │   │   │   │   ├── _add_edit_flashcard_item_bare.html
│   │   │   │   │   │   │   │   │   │   ├── _flashcard_items_list_desktop.html
│   │   │   │   │   │   │   │   │   │   ├── _flashcard_items_list_mobile.html
│   │   │   │   │   │   │   │   │   ├── sets/
│   │   │   │   │   │   │   │   │   │   ├── add_edit_flashcard_set.html
│   │   │   │   │   │   │   │   │   │   ├── flashcard_sets.html
│   │   │   │   │   │   │   │   │   │   ├── _add_edit_flashcard_set_bare.html
│   │   │   │   │   │   │   │   │   │   ├── _flashcard_sets_list.html
│   │   │   │   │   │   │   │   │   ├── shared/
│   │   │   │   │   │   │   │   │   │   ├── _flashcard_audio_control_scripts.html
│   │   │   │   │   │   │   │   │   │   ├── _flashcard_image_control_scripts.html
│   │   │   │   │   │   │   │   ├── quizzes/
│   │   │   │   │   │   │   │   │   ├── excel/
│   │   │   │   │   │   │   │   │   │   ├── manage_quiz_excel.html
│   │   │   │   │   │   │   │   │   ├── items/
│   │   │   │   │   │   │   │   │   │   ├── add_edit_quiz_item.html
│   │   │   │   │   │   │   │   │   │   ├── quiz_items.html
│   │   │   │   │   │   │   │   │   │   ├── _add_edit_quiz_item_bare.html
│   │   │   │   │   │   │   │   │   │   ├── _quiz_items_list.html
│   │   │   │   │   │   │   │   │   ├── sets/
│   │   │   │   │   │   │   │   │   │   ├── add_edit_quiz_set.html
│   │   │   │   │   │   │   │   │   │   ├── quiz_sets.html
│   │   │   │   │   │   │   │   │   │   ├── _add_edit_quiz_set_bare.html
│   │   │   │   │   │   │   │   │   │   ├── _quiz_sets_list.html
│   │   │   │   │   │   │   │   │   ├── shared/
│   │   │   │   │   │   │   │   │   │   ├── _quiz_media_scripts.html
│   │   │   │   │   │   │   │   ├── shared/
│   │   │   │   │   │   │   │   │   ├── _cover_preview_script.html
│   │   │   │   │   │   │   │   │   ├── _shared_styles.html
│   │   │   │   │   │   │   ├── dashboard/
│   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   ├── feedback/
│   │   │   │   │   │   │   │   ├── manage_feedback.html
│   │   │   │   │   │   │   │   ├── _feedback_modal.html
│   │   │   │   │   │   │   │   ├── _feedback_table.html
│   │   │   │   │   │   │   │   ├── _general_feedback_modal.html
│   │   │   │   │   │   │   ├── goals/
│   │   │   │   │   │   │   │   ├── edit.html
│   │   │   │   │   │   │   │   ├── manage.html
│   │   │   │   │   │   │   ├── landing/
│   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   ├── learning/
│   │   │   │   │   │   │   │   ├── sessions.html
│   │   │   │   │   │   │   │   ├── session_summary.html
│   │   │   │   │   │   │   │   ├── collab/
│   │   │   │   │   │   │   │   │   ├── default/
│   │   │   │   │   │   │   │   │   │   ├── dashboard.html
│   │   │   │   │   │   │   │   │   ├── flashcard/
│   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   │   │   ├── _modes_list.html
│   │   │   │   │   │   │   │   │   │   ├── _sets_list.html
│   │   │   │   │   │   │   │   │   │   ├── room/
│   │   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   ├── course/
│   │   │   │   │   │   │   │   │   ├── course_learning_dashboard.html
│   │   │   │   │   │   │   │   │   ├── course_session.html
│   │   │   │   │   │   │   │   │   ├── _base.html
│   │   │   │   │   │   │   │   │   ├── _course_sets_selection.html
│   │   │   │   │   │   │   │   │   ├── _lesson_selection.html
│   │   │   │   │   │   │   │   │   ├── default/
│   │   │   │   │   │   │   │   │   │   ├── course_learning_dashboard.html
│   │   │   │   │   │   │   │   │   │   ├── course_session.html
│   │   │   │   │   │   │   │   │   │   ├── _course_sets_selection.html
│   │   │   │   │   │   │   │   │   │   ├── _lesson_selection.html
│   │   │   │   │   │   │   │   ├── practice/
│   │   │   │   │   │   │   │   │   ├── default/
│   │   │   │   │   │   │   │   │   │   ├── dashboard.html
│   │   │   │   │   │   │   │   │   │   ├── hub.html
│   │   │   │   │   │   │   │   │   │   ├── quiz_dashboard.html
│   │   │   │   │   │   │   │   │   │   ├── setup.html
│   │   │   │   │   │   │   │   │   ├── flashcard/
│   │   │   │   │   │   │   │   │   │   ├── dashboard.html
│   │   │   │   │   │   │   │   │   │   ├── setup.html
│   │   │   │   │   │   │   │   ├── quiz/
│   │   │   │   │   │   │   │   │   ├── battle/
│   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   │   │   ├── room/
│   │   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   │   ├── dashboard/
│   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   │   │   ├── css/
│   │   │   │   │   │   │   │   │   │   │   ├── dashboard.css
│   │   │   │   │   │   │   │   │   │   ├── js/
│   │   │   │   │   │   │   │   │   │   │   ├── dashboard.js
│   │   │   │   │   │   │   │   │   ├── individual/
│   │   │   │   │   │   │   │   │   │   ├── session/
│   │   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   │   │   │   ├── _base.html
│   │   │   │   │   │   │   │   │   │   ├── setup/
│   │   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   │   │   │   ├── default/
│   │   │   │   │   │   │   │   │   │   │   │   ├── _modes_list.html
│   │   │   │   │   │   │   │   │   │   │   │   ├── _quiz_custom_options.html
│   │   │   │   │   │   │   │   │   │   │   │   ├── _quiz_modes_selection_mobile.html
│   │   │   │   │   │   │   │   │   │   │   │   ├── _sets_list.html
│   │   │   │   │   │   │   │   │   │   ├── static/
│   │   │   │   │   │   │   │   │   │   │   ├── css/
│   │   │   │   │   │   │   │   │   │   │   │   ├── session_batch.css
│   │   │   │   │   │   │   │   │   │   │   │   ├── session_single.css
│   │   │   │   │   │   │   │   │   ├── stats/
│   │   │   │   │   │   │   │   │   │   ├── _item_stats_content.html
│   │   │   │   │   │   │   │   │   │   ├── _modal_stats.html
│   │   │   │   │   │   │   │   ├── vocabulary/
│   │   │   │   │   │   │   │   ├── vocab_listening/
│   │   │   │   │   │   │   │   │   ├── session/
│   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   │   ├── setup/
│   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   │   │   ├── default/
│   │   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   ├── vocab_matching/
│   │   │   │   │   │   │   │   │   ├── session/
│   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   ├── vocab_mcq/
│   │   │   │   │   │   │   │   │   ├── session/
│   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   │   ├── setup/
│   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   ├── vocab_speed/
│   │   │   │   │   │   │   │   │   ├── session/
│   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   │   ├── setup/
│   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   ├── vocab_typing/
│   │   │   │   │   │   │   │   │   ├── session/
│   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   │   ├── setup/
│   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   ├── notes/
│   │   │   │   │   │   │   │   ├── manage_notes.html
│   │   │   │   │   │   │   │   ├── _note_panel.html
│   │   │   │   │   │   │   ├── notification/
│   │   │   │   │   │   │   │   ├── .keep
│   │   │   │   │   │   │   │   ├── center.html
│   │   │   │   │   │   │   ├── session/
│   │   │   │   │   │   │   ├── stats/
│   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   ├── system/
│   │   │   │   │   │   │   │   ├── maintenance.html
│   │   │   │   │   │   │   ├── translator/
│   │   │   │   │   │   │   │   ├── history.html
│   │   │   │   │   │   │   ├── user_profile/
│   │   │   │   │   │   │   │   ├── change_password.html
│   │   │   │   │   │   │   │   ├── edit_profile.html
│   │   │   │   │   │   │   │   ├── profile.html
│   │   │   │   │   │   │   │   ├── _base.html
│   │   │   │   │   │   │   ├── vocabulary/
│   │   │   │   │   │   │   │   ├── dashboard/
│   │   │   │   │   │   │   │   │   ├── detail.html
│   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   │   ├── _container_stats_modal.html
│   │   │   │   │   │   │   │   │   ├── _inject_stats_button.html
│   │   │   │   │   │   │   │   │   ├── _item_stats_charts.html
│   │   │   │   │   │   │   │   │   ├── _stats_enhancement.html
│   │   │   │   │   │   │   │   │   ├── components/
│   │   │   │   │   │   │   │   │   │   ├── modals/
│   │   │   │   │   │   │   │   │   │   │   ├── _container_stats_modal.html
│   │   │   │   │   │   │   │   │   │   │   ├── _edit_set_modal.html
│   │   │   │   │   │   │   │   │   │   │   ├── _settings_modal.html
│   │   │   │   │   │   │   │   │   │   ├── stats/
│   │   │   │   │   │   │   │   │   │   │   ├── _inject_stats_button.html
│   │   │   │   │   │   │   │   │   │   │   ├── _item_stats_charts.html
│   │   │   │   │   │   │   │   │   │   │   ├── _stats_enhancement.html
│   │   │   │   │   │   │   │   │   │   ├── steps/
│   │   │   │   │   │   │   │   │   │   │   ├── _flashcard_options.html
│   │   │   │   │   │   │   │   │   │   │   ├── _mcq_options.html
│   │   │   │   │   │   │   │   │   │   │   ├── _modes.html
│   │   │   │   │   │   │   │   │   ├── css/
│   │   │   │   │   │   │   │   │   ├── js/
│   │   │   │   │   │   │   │   │   │   ├── dashboard.js
│   │   │   │   │   │   │   │   ├── flashcard/
│   │   │   │   │   │   │   │   │   ├── components/
│   │   │   │   │   │   │   │   │   │   ├── _memory_power_widget.html
│   │   │   │   │   │   │   │   │   ├── session/
│   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   │   ├── setup/
│   │   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   ├── modes/
│   │   │   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   │   ├── stats/
│   │   │   │   │   │   │   │   │   ├── item_detail.html
│   │   │   │   │   │   │   │   │   ├── item_stats_modal.html
│   │   │   │   │   │   │   │   │   ├── _item_stats_content.html
│   │   │   │   │   │   │   │   │   ├── _modal_stats.html
│   │   │   │   │   │   │   ├── vocab_flashcard/
│   │   │   │   │   │   │   │   ├── session.html
│   │   │   │   │   │   │   │   ├── setup.html
│   │   │   │   │   │   │   │   ├── summary.html
│   │   │   │   │   │   │   │   ├── _modes_list.html
│   │   │   │   │   │   │   │   ├── _sets_list.html
│   │   │   │   │   │   │   │   ├── components/
│   │   │   │   │   │   │   │   │   ├── card.html
│   │   │   │   │   ├── maintenance/
│   │   │   │   │   │   ├── maintenance.html
│   │   ├── utils/
│   │   │   ├── bbcode_parser.py
│   │   │   ├── content_renderer.py
│   │   │   ├── db_session.py
│   │   │   ├── excel.py
│   │   │   ├── html_sanitizer.py
│   │   │   ├── media_paths.py
│   │   │   ├── pagination.py
│   │   │   ├── search.py
│   │   │   ├── template_filters.py
│   │   │   ├── template_helpers.py
│   │   │   ├── time_utils.py
│   │   │   ├── __init__.py
│   ├── scripts/
│   │   ├── add_fsrs_columns.py
│   │   ├── debug_crash.py
│   │   ├── debug_fsrs_data.py
│   │   ├── debug_modes_crash.py
│   │   ├── fix_fsrs_difficulty.py
│   │   ├── fix_missing_columns.py
│   │   ├── init_db_tables.py
│   │   ├── migrate_review_to_study_logs.py
│   │   ├── migrate_to_fsrs.py
│   │   ├── migrate_to_item_memory_state.py
│   │   ├── rename_fsrs_columns.py
│   │   ├── standalone_migration.py
│   │   ├── test_anki_selection.py
│   │   ├── test_session_resume.py
│   │   ├── update_schema.py
│   ├── tests/
```
