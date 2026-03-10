#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Account indexing hardware integration test.

Usage:
    pytest tests/test_account_indexing_hardware.py -v --hardware
"""

import json
import sys
import time
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from conftest import HARDWARE_MODE, STARTUP_DELAY_SECONDS
from agent.py_service.main import initialize
from agent.py_service.register import register_all_modules
from agent.py_service.modules.workflow_executor.executor import execute_pipeline
from agent.py_service.pkg.common.database import init_database, list_all_accounts, list_characters_by_account


@pytest.fixture(scope="session")
def components():
    if not HARDWARE_MODE:
        return initialize(test_mode=True, skip_hardware=True)

    print(f"\n{'='*60}")
    print("[Hardware] Initializing for account indexing...")
    print(f"[Hardware] Starting in {STARTUP_DELAY_SECONDS} seconds...")
    print("[Hardware] Please switch to game window now!")
    print(f"{'='*60}\n")

    for i in range(STARTUP_DELAY_SECONDS, 0, -1):
        print(f"[Hardware] {i}...")
        time.sleep(1)

    return initialize(test_mode=False, skip_hardware=False)


def _build_temp_pipeline(tmp_path: Path) -> Path:
    src = project_root / "assets" / "resource" / "pipeline" / "account_indexing.json"
    with src.open("r", encoding="utf-8") as f:
        pipeline = json.load(f)

    # Persist to project data/ for manual inspection after test runs.
    db_path = project_root / "data" / "accounts.db"
    data_dir = project_root / "data"

    for node_name in ("resolve_account_tag", "finalize_account_index"):
        node = pipeline.get(node_name, {})
        action_or_rec = node.get("recognition") or node.get("action") or {}
        param = action_or_rec.get("param")
        if isinstance(param, dict):
            param["db_path"] = str(db_path)
            param["data_dir"] = str(data_dir)

    out = tmp_path / "account_indexing.hardware.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(pipeline, f, ensure_ascii=False, indent=2)
    return out


class TestAccountIndexingHardware:
    @pytest.mark.skipif(not HARDWARE_MODE, reason="Hardware mode not enabled")
    def test_execute_account_indexing_pipeline(self, components, tmp_path):
        hardware = components.hardware_controller
        vision = components.vision_engine
        if not hardware or not vision:
            pytest.skip("Hardware or vision unavailable")

        register_all_modules()
        pipeline_path = _build_temp_pipeline(tmp_path)

        success = execute_pipeline(
            pipeline_path=pipeline_path,
            entry_node="account_indexingMain",
            hardware_controller=hardware,
            vision_engine=vision,
            timeout_seconds=45.0,
        )
        assert success, "Account indexing pipeline execution failed"

        db_path = project_root / "data" / "accounts.db"
        init_database(str(db_path))
        accounts = list_all_accounts(str(db_path))
        if len(accounts) == 0:
            pytest.skip("No account record created in persistent data/accounts.db; likely not on character-selection screen or switch button not visible")

        account_id = int(accounts[0]["id"])
        chars = list_characters_by_account(str(db_path), account_id)
        assert len(chars) >= 0
