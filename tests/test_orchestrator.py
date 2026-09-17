import os
import sys
import pytest

from scripts.orchestrator import BotManager, BotProcess


class TestOrchestrator:

    def test_bot_process_init(self):
        info = {
            "name": "test-bot-1",
            "role": "patrol",
            "port": 3005,
            "district": "Haute ville",
        }
        bp = BotProcess(info, "dummy_script.py")
        assert bp.name == "test-bot-1"
        assert bp.role == "patrol"
        assert bp.port == 3005
        assert bp.district == "Haute ville"
        assert not bp.is_alive()

    def test_bot_manager_init(self):
        test_fleet = [
            {"name": "leader", "role": "leader", "port": 3000},
            {"name": "patrol-1", "role": "patrol", "port": 3001, "district": "place george orwell"},
        ]
        bm = BotManager(fleet_config=test_fleet, stagger_delay=3)
        assert len(bm.bots) == 2
        assert "leader" in bm.bots
        assert "patrol-1" in bm.bots
        assert bm.bots["leader"].port == 3000
        assert bm.bots["patrol-1"].port == 3001
        assert bm.stagger_delay == 3
