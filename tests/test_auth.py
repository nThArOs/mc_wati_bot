import os
import shutil
import tempfile
import time
import pytest

from utils.auth_manager import (
    TOTPManager,
    TokenManager,
    MfaDeviceCodeHandler,
)


class TestTOTPManager:

    def test_rfc6238_vector(self):
        # RFC 6238 test vectors: Secret = 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ' (Base32 of '12345678901234567890')
        # Time = 59s -> Expected code 287082
        secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        manager = TOTPManager(secret)
        code, remaining = manager.generate_code(timestamp=59)
        assert code == "287082"
        assert remaining == 30 - (59 % 30)

    def test_clean_secret(self):
        secret = "jbsw y3dp - ehpk 3pxp"
        cleaned = TOTPManager._clean_secret(secret)
        assert cleaned == "JBSWY3DPEHPK3PXP"

    def test_unconfigured(self):
        manager = TOTPManager()
        assert not manager.is_configured()
        code, rem = manager.generate_code()
        assert code is None
        assert rem == 0

    def test_verify_code(self):
        manager = TOTPManager("JBSWY3DPEHPK3PXP")
        code, _ = manager.generate_code()
        assert manager.verify_code(code)
        assert not manager.verify_code("000000")
        assert not manager.verify_code("")
        assert not manager.verify_code(None)


class TestTokenManager:

    @pytest.fixture
    def temp_tokens_dir(self):
        temp_dir = tempfile.mkdtemp(prefix="test_tokens_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_profile_creation(self, temp_tokens_dir):
        tm = TokenManager("bot_test", base_dir=temp_tokens_dir)
        profile_path = tm.get_profile_path()
        assert os.path.exists(profile_path)
        assert not tm.has_cached_tokens()

    def test_token_caching_and_summary(self, temp_tokens_dir):
        tm = TokenManager("bot_test", base_dir=temp_tokens_dir)
        token_file = os.path.join(tm.get_profile_path(), "msa-cache.json")
        with open(token_file, "w", encoding="utf-8") as f:
            f.write('{"username": "Steve_Test", "token": "abc123xyz"}')

        assert tm.has_cached_tokens()
        summary = tm.get_token_summary()
        assert summary["has_tokens"] is True
        assert summary["file_count"] == 1
        assert summary["account_hint"] == "Steve_Test"
        assert "msa-cache.json" in summary["files"]

    def test_clear_tokens(self, temp_tokens_dir):
        tm = TokenManager("bot_test", base_dir=temp_tokens_dir)
        token_file = os.path.join(tm.get_profile_path(), "msa-cache.json")
        with open(token_file, "w", encoding="utf-8") as f:
            f.write('{"username": "Steve_Test"}')

        assert tm.has_cached_tokens()
        deleted = tm.clear_tokens()
        assert deleted == 1
        assert not tm.has_cached_tokens()


class TestMfaDeviceCodeHandler:

    def test_on_msa_code(self):
        logged_messages = []
        handler = MfaDeviceCodeHandler(
            bot_name="test_bot",
            totp_manager=TOTPManager("JBSWY3DPEHPK3PXP"),
            auto_open_browser=False,
            logger=lambda msg: logged_messages.append(msg),
        )

        data = {
            "user_code": "XYZ-9876",
            "verification_uri": "https://microsoft.com/devicelogin",
            "expires_in": 900,
        }
        handler.on_msa_code(data)

        assert handler.last_code_info["user_code"] == "XYZ-9876"
        assert handler.last_code_info["verification_uri"] == "https://microsoft.com/devicelogin"
        assert any("XYZ-9876" in msg for msg in logged_messages)
