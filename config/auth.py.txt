# ============================================================
# CONFIGURATION AUTHENTIFICATION MICROSOFT & 2FA
# ============================================================

import os
import re

# Base directory for persistent OAuth and Refresh token storage
AUTH_TOKENS_DIR = os.getenv("AUTH_TOKENS_DIR", "./tokens")

# Automatically open Microsoft Device Code login page in default browser
AUTO_OPEN_BROWSER = (
    os.getenv("AUTO_OPEN_BROWSER", "true").lower() in ("true", "1", "yes")
)

# Base32 shared secret for automated TOTP 2FA code generation (RFC 6238)
# Example: "JBSWY3DPEHPK3PXP" (leave empty if using manual phone authenticator)
MICROSOFT_TOTP_SECRET = os.getenv("MICROSOFT_TOTP_SECRET", "")

# Optional credentials for automated headless login via Selenium
MICROSOFT_EMAIL = (
    os.getenv("MICROSOFT_EMAIL", "") or os.getenv("MICROSOFT_MAIL", "")
)
MICROSOFT_PASSWORD = os.getenv("MICROSOFT_PASSWORD", "")
ENABLE_HEADLESS_AUTH = (
    os.getenv("ENABLE_HEADLESS_AUTH", "false").lower() in ("true", "1", "yes")
)


# ============================================================
# RÉSOLUTION DYNAMIQUE DES IDENTIFIANTS PAR BOT
# ============================================================

def get_bot_credentials(bot_name):
    """Résout les identifiants spécifiques à un bot ou génériques."""
    clean_name = re.sub(r"[^a-zA-Z0-9]", "_", bot_name).upper()

    email = (
        os.getenv(f"{clean_name}_MICROSOFT_EMAIL")
        or os.getenv(f"{clean_name}_MICROSOFT_MAIL")
        or os.getenv(f"{clean_name}_EMAIL")
        or os.getenv(f"{clean_name}_MAIL")
        or os.getenv(f"MICROSOFT_EMAIL_{clean_name}")
        or os.getenv(f"MICROSOFT_MAIL_{clean_name}")
        or os.getenv("MICROSOFT_EMAIL")
        or os.getenv("MICROSOFT_MAIL", "")
    )

    password = (
        os.getenv(f"{clean_name}_MICROSOFT_PASSWORD")
        or os.getenv(f"{clean_name}_PASSWORD")
        or os.getenv(f"MICROSOFT_PASSWORD_{clean_name}")
        or os.getenv("MICROSOFT_PASSWORD", "")
    )

    totp_secret = (
        os.getenv(f"{clean_name}_MICROSOFT_TOTP_SECRET")
        or os.getenv(f"{clean_name}_TOTP_SECRET")
        or os.getenv(f"MICROSOFT_TOTP_SECRET_{clean_name}")
        or os.getenv("MICROSOFT_TOTP_SECRET", "")
    )

    return {
        "email": email,
        "password": password,
        "totp_secret": totp_secret,
    }
