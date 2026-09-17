# ============================================================
# TESTS UNITAIRES : SÉLECTEUR DE BOTS (mc_wati_bot)
# ============================================================

import os
import pytest
from utils.bot_selector import (
    parse_bot_selection,
    get_available_bots,
    DEFAULT_BOT_CONFIG,
)
from utils.auth_manager import get_bot_credentials


class TestBotSelector:

    def test_get_available_bots_structure(self):
        bots = get_available_bots()
        assert len(bots) >= 2
        names = [b["name"] for b in bots]
        assert "Moisurunautrecom" in names
        assert "nThArOs" in names

    def test_parse_single_choice_1(self):
        selected = parse_bot_selection("1")
        assert len(selected) == 1
        assert selected[0]["name"] == "Moisurunautrecom"

    def test_parse_single_choice_2(self):
        selected = parse_bot_selection("2")
        assert len(selected) == 1
        assert selected[0]["name"] == "nThArOs"

    def test_parse_multiple_comma(self):
        selected = parse_bot_selection("1,2")
        assert len(selected) == 2
        assert selected[0]["name"] == "Moisurunautrecom"
        assert selected[1]["name"] == "nThArOs"

    def test_parse_multiple_space(self):
        selected = parse_bot_selection("1 2")
        assert len(selected) == 2
        names = [b["name"] for b in selected]
        assert "Moisurunautrecom" in names
        assert "nThArOs" in names

    def test_parse_multiple_french_and(self):
        selected = parse_bot_selection("1 et 2")
        assert len(selected) == 2

    def test_parse_all_keyword(self):
        for kw in ("all", "tous", "both", "*", "3"):
            selected = parse_bot_selection(kw)
            assert len(selected) == 2

    def test_parse_by_name(self):
        selected = parse_bot_selection("nThArOs")
        assert len(selected) == 1
        assert selected[0]["name"] == "nThArOs"

        selected_case = parse_bot_selection("moisurunautrecom")
        assert len(selected_case) == 1
        assert selected_case[0]["name"] == "Moisurunautrecom"

    def test_parse_empty_defaults_to_1(self):
        selected = parse_bot_selection("")
        assert len(selected) == 1
        assert selected[0]["name"] == "Moisurunautrecom"

    def test_parse_invalid_falls_back(self):
        selected = parse_bot_selection("invalid_choice_xyz")
        assert len(selected) == 1
        assert selected[0]["name"] == "Moisurunautrecom"


class TestBotCredentialsResolver:

    def test_get_bot_credentials_fallback(self, monkeypatch):
        monkeypatch.setenv("MICROSOFT_EMAIL", "default@test.com")
        monkeypatch.setenv("MICROSOFT_PASSWORD", "secret123")
        monkeypatch.setenv("MICROSOFT_TOTP_SECRET", "JBSWY3DPEHPK3PXP")

        creds = get_bot_credentials("nThArOs")
        assert creds["email"] == "default@test.com"
        assert creds["password"] == "secret123"
        assert creds["totp_secret"] == "JBSWY3DPEHPK3PXP"

    def test_get_bot_credentials_specific_override(self, monkeypatch):
        monkeypatch.setenv("MICROSOFT_EMAIL", "default@test.com")
        monkeypatch.setenv("NTHAROS_EMAIL", "ntharos@custom.com")
        monkeypatch.setenv("NTHAROS_PASSWORD", "custompwd")
        monkeypatch.setenv("NTHAROS_TOTP_SECRET", "CUSTOMTOTPSECRET")

        creds = get_bot_credentials("nThArOs")
        assert creds["email"] == "ntharos@custom.com"
        assert creds["password"] == "custompwd"
        assert creds["totp_secret"] == "CUSTOMTOTPSECRET"

    def test_get_bot_credentials_microsoft_mail_alias(self, monkeypatch):
        monkeypatch.delenv("MICROSOFT_EMAIL", raising=False)
        monkeypatch.setenv("MICROSOFT_MAIL", "mail_alias@test.com")

        creds = get_bot_credentials("nThArOs")
        assert creds["email"] == "mail_alias@test.com"
