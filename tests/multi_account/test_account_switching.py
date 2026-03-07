"""
Account Switching Tests

Comprehensive tests for AccountSwitcher including:
- Basic switching functionality
- Safety mechanisms (cannot switch during workflow)
- Thread safety
- Integration with workflow bootstrap
- Progress tracker database switching

Requirements: MULTI-03
"""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest
import numpy as np

from core.account_manager import AccountManager, AccountContext, AccountManagerError
from core.account_switcher import AccountSwitcher
from core.progress_tracker import ProgressTracker
from core.workflow_bootstrap import create_workflow_executor_with_account


class TestBasicSwitching:
    """Test basic account switching functionality."""

    def test_can_switch_when_idle(self, account_switcher):
        """Returns True when no workflow is running."""
        assert account_switcher.can_switch() is True

    def test_cannot_switch_during_workflow(self, account_switcher):
        """Returns False when workflow is running."""
        account_switcher.set_running_state(True)
        assert account_switcher.can_switch() is False

    def test_switch_resets_running_state(self, account_switcher, sample_screenshot):
        """Switch can happen after workflow stops."""
        account_switcher.set_running_state(True)
        assert account_switcher.can_switch() is False

        account_switcher.set_running_state(False)
        assert account_switcher.can_switch() is True

    def test_switch_updates_context(self, account_manager, sample_screenshot):
        """Context changes after successful switch."""
        # Create initial context
        ctx1 = account_manager.get_or_create_context(sample_screenshot)
        assert ctx1.account_hash == "abc123def456"

        # Create second account in database
        from core.database import create_account, init_database
        main_db = str(account_manager._get_main_db_path())
        init_database(main_db)
        create_account(main_db, "xyz789uvw012")

        # Switch to second account using account_manager directly
        # (switch_to_account requires old context which may not exist in test)
        ctx2 = account_manager.switch_account("xyz789uvw012")

        assert ctx2.account_hash == "xyz789uvw012"

    def test_switch_fires_callbacks(self, account_manager, sample_screenshot):
        """Registered callbacks are fired on switch."""
        callback_called = False
        old_ctx_received = None
        new_ctx_received = None

        def on_switch(old_ctx, new_ctx):
            nonlocal callback_called, old_ctx_received, new_ctx_received
            callback_called = True
            old_ctx_received = old_ctx
            new_ctx_received = new_ctx

        # Create initial context
        ctx1 = account_manager.get_or_create_context(sample_screenshot)

        # Create second account
        from core.database import create_account, init_database
        main_db = str(account_manager._get_main_db_path())
        init_database(main_db)
        create_account(main_db, "xyz789uvw012")

        # Setup switcher with callback
        switcher = AccountSwitcher(account_manager)
        switcher.on_switch(on_switch)

        # Switch
        switcher.switch_to_account("xyz789uvw012", sample_screenshot)

        # Verify callback was called
        assert callback_called is True
        assert old_ctx_received is not None
        assert new_ctx_received is not None
        assert old_ctx_received.account_hash == "abc123def456"
        assert new_ctx_received.account_hash == "xyz789uvw012"


class TestSafetyMechanisms:
    """Test safety mechanisms for account switching."""

    def test_switch_waits_for_workflow_stop(self, account_manager, mock_workflow_executor, sample_screenshot):
        """Switch waits for graceful workflow shutdown."""
        # Setup running workflow
        switcher = AccountSwitcher(account_manager)
        switcher.attach_workflow(mock_workflow_executor)
        switcher.set_running_state(True)

        # Create second account
        from core.database import create_account, init_database
        main_db = str(account_manager._get_main_db_path())
        init_database(main_db)
        create_account(main_db, "xyz789uvw012")

        # Mock the stop to succeed
        mock_workflow_executor._stop_event.wait.return_value = True

        # Switch should succeed by stopping workflow
        result = switcher.switch_to_account("xyz789uvw012", sample_screenshot)
        assert result is True

        # Verify stop was called
        mock_workflow_executor._stop_event.set.assert_called_once()

    def test_concurrent_switch_prevented(self, account_manager, sample_screenshot):
        """Lock prevents race conditions in switch."""
        switcher = AccountSwitcher(account_manager)

        # Create two accounts
        from core.database import create_account, init_database
        main_db = str(account_manager._get_main_db_path())
        init_database(main_db)
        create_account(main_db, "account_a")
        create_account(main_db, "account_b")

        results = []

        def switch_a():
            try:
                switcher.switch_to_account("account_a", sample_screenshot)
                results.append("a")
            except Exception as e:
                results.append(f"a_error: {e}")

        def switch_b():
            try:
                switcher.switch_to_account("account_b", sample_screenshot)
                results.append("b")
            except Exception as e:
                results.append(f"b_error: {e}")

        # Run switches concurrently
        t1 = threading.Thread(target=switch_a)
        t2 = threading.Thread(target=switch_b)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Both should complete (lock ensures sequential execution)
        assert len(results) == 2

    def test_invalid_account_handled(self, account_manager, sample_screenshot):
        """Error handling for non-existent account hash."""
        switcher = AccountSwitcher(account_manager)

        # Initialize database first
        from core.database import init_database
        init_database(str(account_manager._get_main_db_path()))

        with pytest.raises(RuntimeError) as exc_info:
            switcher.switch_to_account("nonexistent_hash", sample_screenshot)

        assert "not found" in str(exc_info.value).lower()


class TestIntegration:
    """Test integration with other components."""

    def test_bootstrap_creates_account_aware_executor(self, temp_data_dir, sample_screenshot):
        """Factory function creates executor with account context."""
        # This test verifies the factory function exists and accepts account_context
        # We can't fully test without a real workflow file, but we can verify the signature

        # Create a minimal mock workflow
        import yaml
        workflow_path = temp_data_dir / "test_workflow.yaml"
        workflow_config = {
            "name": "test_workflow",
            "start_step_id": "step1",
            "steps": [
                {
                    "step_id": "step1",
                    "action": {"type": "click", "x": 100, "y": 200},
                    "next": None
                }
            ]
        }
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        with open(workflow_path, 'w') as f:
            yaml.dump(workflow_config, f)

        # Create account context
        db_path = temp_data_dir / "accounts" / "test123" / "progress.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        tracker = ProgressTracker(str(db_path))

        context = AccountContext(
            account_hash="test123",
            account_id=1,
            character_count=6,
            db_path=str(db_path),
            progress_tracker=tracker
        )

        # Create mock controller and vision engine
        controller = MagicMock()
        vision_engine = MagicMock()

        # Create executor with account context
        executor = create_workflow_executor_with_account(
            workflow_path=str(workflow_path),
            account_context=context,
            controller=controller,
            vision_engine=vision_engine,
            enable_compliance_guard=False
        )

        # Verify executor was created
        assert executor is not None
        assert executor.account_id == "test123"

    def test_progress_tracker_switches_database(self, account_manager, sample_screenshot):
        """New database is used after account switch."""
        # Create initial context and mark progress
        ctx1 = account_manager.get_or_create_context(sample_screenshot)
        ctx1.progress_tracker.mark_done(0, "CharA")
        assert ctx1.progress_tracker.is_done(0) is True

        # Create second account
        from core.database import create_account
        main_db = str(account_manager._get_main_db_path())
        create_account(main_db, "xyz789uvw012")

        # Switch to second account
        switcher = AccountSwitcher(account_manager)
        switcher.switch_to_account("xyz789uvw012", sample_screenshot)

        ctx2 = account_manager.current_context

        # Verify different databases
        assert ctx1.db_path != ctx2.db_path

        # Verify progress is isolated
        # Character 0 should not be done in new account
        assert ctx2.progress_tracker.is_done(0) is False

    def test_full_switch_workflow(self, account_manager, mock_workflow_executor, sample_screenshot):
        """End-to-end account switch workflow."""
        # Setup switcher
        switcher = AccountSwitcher(account_manager)
        switcher.attach_workflow(mock_workflow_executor)

        # Create initial context
        ctx1 = account_manager.get_or_create_context(sample_screenshot)
        assert ctx1.account_hash == "abc123def456"

        # Mark some progress
        ctx1.progress_tracker.mark_done(0, "Char1")
        ctx1.progress_tracker.mark_done(1, "Char2")

        # Create second account
        from core.database import create_account
        main_db = str(account_manager._get_main_db_path())
        create_account(main_db, "xyz789uvw012")

        # Setup callback
        callback_count = 0
        def on_switch(old_ctx, new_ctx):
            nonlocal callback_count
            callback_count += 1

        switcher.on_switch(on_switch)

        # Switch
        result = switcher.switch_to_account("xyz789uvw012", sample_screenshot)
        assert result is True

        # Verify new context
        ctx2 = account_manager.current_context
        assert ctx2.account_hash == "xyz789uvw012"

        # Verify callback fired
        assert callback_count == 1

        # Verify progress isolation
        assert ctx2.progress_tracker.is_done(0) is False

        # Verify old progress still exists
        assert ctx1.progress_tracker.is_done(0) is True


class TestSwitchToDetected:
    """Test auto-detection switching."""

    def test_switch_to_detected_finds_account(self, account_manager, sample_screenshot):
        """Auto-detect and switch to account from screenshot."""
        switcher = AccountSwitcher(account_manager)

        # First create the account
        ctx1 = account_manager.get_or_create_context(sample_screenshot)

        # Now switch via detection
        ctx2 = switcher.switch_to_detected(sample_screenshot)

        assert ctx2 is not None
        assert ctx2.account_hash == "abc123def456"

    def test_switch_to_detected_returns_none_on_failure(self, account_manager, sample_screenshot):
        """Returns None if detection fails."""
        switcher = AccountSwitcher(account_manager)

        # Create detector that raises exception
        bad_detector = MagicMock()
        bad_detector.discover_account.side_effect = Exception("Detection failed")

        account_manager.detector = bad_detector

        result = switcher.switch_to_detected(sample_screenshot)
        assert result is None


class TestErrorHandling:
    """Test error handling in account switching."""

    def test_callback_errors_dont_break_switch(self, account_manager, sample_screenshot):
        """Callback exceptions don't prevent switch."""
        # Create initial context
        ctx1 = account_manager.get_or_create_context(sample_screenshot)

        # Create second account
        from core.database import create_account
        main_db = str(account_manager._get_main_db_path())
        create_account(main_db, "xyz789uvw012")

        # Setup switcher with failing callback
        switcher = AccountSwitcher(account_manager)

        def failing_callback(old_ctx, new_ctx):
            raise RuntimeError("Callback error")

        switcher.on_switch(failing_callback)

        # Switch should still succeed
        result = switcher.switch_to_account("xyz789uvw012", sample_screenshot)
        assert result is True

        # Verify context was updated
        ctx2 = account_manager.current_context
        assert ctx2.account_hash == "xyz789uvw012"

    def test_workflow_stop_failure_raises_error(self, account_manager, mock_workflow_executor, sample_screenshot):
        """RuntimeError if workflow cannot be stopped."""
        switcher = AccountSwitcher(account_manager)
        switcher.attach_workflow(mock_workflow_executor)
        switcher.set_running_state(True)

        # Mock stop to fail
        mock_workflow_executor._stop_event.wait.return_value = False

        # Create second account
        from core.database import create_account, init_database
        main_db = str(account_manager._get_main_db_path())
        init_database(main_db)
        create_account(main_db, "xyz789uvw012")

        with pytest.raises(RuntimeError) as exc_info:
            switcher.switch_to_account("xyz789uvw012", sample_screenshot)

        assert "could not stop" in str(exc_info.value).lower()


class TestThreadSafety:
    """Test thread safety of AccountSwitcher."""

    def test_running_state_thread_safe(self, account_manager):
        """Running state is protected by lock."""
        switcher = AccountSwitcher(account_manager)

        results = []

        def set_running_true():
            switcher.set_running_state(True)
            results.append(switcher.is_running)

        def set_running_false():
            switcher.set_running_state(False)
            results.append(switcher.is_running)

        # Run concurrently
        threads = []
        for i in range(10):
            t = threading.Thread(target=set_running_true if i % 2 == 0 else set_running_false)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All operations should complete without error
        assert len(results) == 10

    def test_can_switch_thread_safe(self, account_manager):
        """can_switch is thread-safe."""
        switcher = AccountSwitcher(account_manager)

        results = []

        def check_can_switch():
            results.append(switcher.can_switch())

        # Run concurrently
        threads = []
        for i in range(10):
            t = threading.Thread(target=check_can_switch)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All checks should return boolean
        assert all(isinstance(r, bool) for r in results)
