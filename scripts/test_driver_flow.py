# File: scripts/test_driver_flow.py
"""
Session Driver Flow Test
========================
Standalone script to verify the Session Driver Pattern end-to-end.

Usage:
    cd newmindstack
    python scripts/test_driver_flow.py
"""

import sys
import os
import traceback

# ── Ensure project root is on sys.path ───────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'))


def main():
    print("=" * 60)
    print("  SESSION DRIVER FLOW TEST")
    print("=" * 60)
    print()

    # ── Step 0: Setup App Context ────────────────────────────────────
    print("[SETUP] Creating Flask app...")
    try:
        from mindstack_app import create_app
        app = create_app()
        ctx = app.app_context()
        ctx.push()
        print("[SETUP] App context pushed ✅")
    except Exception:
        print("[SETUP] Failed to create app ❌")
        traceback.print_exc()
        return

    # ── Step 0b: Find test data ──────────────────────────────────────
    print("[SETUP] Looking for test user and container...")
    try:
        from mindstack_app.models import db, LearningContainer, LearningItem
        from mindstack_app.modules.auth.models import User

        user = db.session.query(User).first()
        if not user:
            print("[SETUP] No users found in DB ❌ — Create a user first.")
            return
        user_id = user.user_id
        print(f"[SETUP] User: {user.username} (ID: {user_id}) ✅")

        # Find a flashcard container that has items
        container = (
            db.session.query(LearningContainer)
            .filter(LearningContainer.container_type == 'FLASHCARD_SET')
            .first()
        )
        if not container:
            print("[SETUP] No FLASHCARD_SET containers found ❌ — Create vocabulary sets first.")
            return

        item_count = (
            db.session.query(LearningItem)
            .filter_by(container_id=container.container_id)
            .count()
        )
        if item_count == 0:
            print(f"[SETUP] Container '{container.title}' has 0 items ❌")
            return

        container_id = container.container_id
        print(f"[SETUP] Container: '{container.title}' (ID: {container_id}, {item_count} items) ✅")

    except Exception:
        print("[SETUP] Failed to find test data ❌")
        traceback.print_exc()
        return

    print()
    print("-" * 60)
    print("  RUNNING TESTS")
    print("-" * 60)
    print()

    # ══════════════════════════════════════════════════════════════════
    # TEST 1: Start a driven session
    # ══════════════════════════════════════════════════════════════════
    print("[TEST 1] Starting driven session (mode=mcq)...")
    db_session = None
    driver_state = None
    try:
        from mindstack_app.modules.session.services.session_service import LearningSessionService

        db_session, driver_state = LearningSessionService.start_driven_session(
            user_id=user_id,
            container_id=container_id,
            learning_mode='mcq',
            settings={'num_choices': 4},
        )

        assert db_session is not None, "db_session is None"
        assert driver_state is not None, "driver_state is None"
        assert driver_state.total_items > 0, f"total_items is {driver_state.total_items}"

        session_id = db_session.session_id
        print(f"[TEST 1] ✅ Session created — ID: {session_id}, "
              f"Total items: {driver_state.total_items}, "
              f"Queue: {len(driver_state.item_queue)} items")

    except Exception:
        print("[TEST 1] ❌ FAILED")
        traceback.print_exc()
        return

    # ══════════════════════════════════════════════════════════════════
    # TEST 2: Get next interaction
    # ══════════════════════════════════════════════════════════════════
    print()
    print("[TEST 2] Fetching next interaction...")
    payload = None
    try:
        from mindstack_app.modules.session.drivers.registry import DriverRegistry

        driver = DriverRegistry.resolve('mcq')
        payload = driver.get_next_interaction(driver_state)

        assert payload is not None, "payload is None (queue empty?)"
        assert payload.item_id is not None, "item_id is None"
        assert payload.interaction_type == 'mcq', f"type is {payload.interaction_type}"
        assert 'question' in payload.data, f"missing 'question' in data: {list(payload.data.keys())}"
        assert 'choices' in payload.data, f"missing 'choices' in data"

        choices_str = ' | '.join(payload.data['choices'][:4])
        print(f"[TEST 2] ✅ Interaction received:")
        print(f"         Item ID: {payload.item_id}")
        print(f"         Question: {payload.data['question'][:80]}")
        print(f"         Choices: [{choices_str}]")
        print(f"         Progress: {payload.progress}")

    except Exception:
        print("[TEST 2] ❌ FAILED")
        traceback.print_exc()
        return

    # ══════════════════════════════════════════════════════════════════
    # TEST 3a: Submit CORRECT answer
    # ══════════════════════════════════════════════════════════════════
    print()
    print("[TEST 3a] Submitting CORRECT answer...")
    try:
        correct_index = payload.data.get('correct_index', 0)
        user_input_correct = {
            'item_id': payload.item_id,
            'answer_index': correct_index,
            'correct_index': correct_index,
        }

        result = LearningSessionService.submit_answer(session_id, user_input_correct)

        assert result is not None, "result is None"
        assert result['is_correct'] is True, f"expected correct, got {result['is_correct']}"
        assert result['score_change'] > 0, f"score_change is {result['score_change']}"

        print(f"[TEST 3a] ✅ Result: Correct! (+{result['score_change']} pts)")
        print(f"          Quality: {result['quality']}, "
              f"SRS update: {'yes' if result.get('srs_update') else 'no'}")

    except Exception:
        print("[TEST 3a] ❌ FAILED")
        traceback.print_exc()
        return

    # ══════════════════════════════════════════════════════════════════
    # TEST 3b: Submit WRONG answer (next item)
    # ══════════════════════════════════════════════════════════════════
    print()
    print("[TEST 3b] Fetching next item and submitting WRONG answer...")
    try:
        payload2 = driver.get_next_interaction(driver_state)

        if payload2 is None:
            print("[TEST 3b] ⏭️  SKIPPED — no more items in queue")
        else:
            correct_idx = payload2.data.get('correct_index', 0)
            wrong_idx = (correct_idx + 1) % len(payload2.data.get('choices', [1, 2]))

            user_input_wrong = {
                'item_id': payload2.item_id,
                'answer_index': wrong_idx,
                'correct_index': correct_idx,
            }

            result2 = LearningSessionService.submit_answer(session_id, user_input_wrong)

            assert result2 is not None, "result is None"
            assert result2['is_correct'] is False, f"expected wrong, got {result2['is_correct']}"

            print(f"[TEST 3b] ✅ Result: Incorrect (as expected)")
            print(f"          Quality: {result2['quality']}, Score: {result2['score_change']}")

    except Exception:
        print("[TEST 3b] ❌ FAILED")
        traceback.print_exc()
        return

    # ══════════════════════════════════════════════════════════════════
    # TEST 4: Finalize session
    # ══════════════════════════════════════════════════════════════════
    print()
    print("[TEST 4] Finalizing session...")
    try:
        summary = driver.finalize_session(driver_state)

        print(f"[TEST 4] ✅ Session Summary:")
        print(f"          Total: {summary.total_items} | "
              f"Correct: {summary.correct} | "
              f"Incorrect: {summary.incorrect}")
        print(f"          Accuracy: {summary.accuracy}% | "
              f"XP: {summary.xp_earned} | "
              f"Duration: {summary.duration_seconds}s")

        # Also complete in DB
        LearningSessionService.complete_session(session_id)
        print(f"[TEST 4] ✅ DB session marked as completed")

    except Exception:
        print("[TEST 4] ❌ FAILED")
        traceback.print_exc()
        return

    # ── Summary ──────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  ALL TESTS PASSED ✅")
    print("=" * 60)
    print()
    print("Driver flow verified:")
    print("  start_driven_session → get_next_interaction → submit_answer → finalize_session")
    print()

    ctx.pop()


if __name__ == '__main__':
    main()
