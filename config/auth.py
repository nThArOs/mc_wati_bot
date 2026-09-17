import os

# Base directory for persistent OAuth and Refresh token storage
AUTH_TOKENS_DIR = os.getenv("AUTH_TOKENS_DIR", "./tokens")

# Automatically open Microsoft Device Code login page in default browser
AUTO_OPEN_BROWSER = os.getenv("AUTO_OPEN_BROWSER", "true").lower() in ("true", "1", "yes")

# Base32 shared secret for automated TOTP 2FA code generation (RFC 6238)
# Example: "JBSWY3DPEHPK3PXP" (leave empty if using manual phone authenticator)
MICROSOFT_TOTP_SECRET = os.getenv("MICROSOFT_TOTP_SECRET", "")

# Optional credentials for automated headless login via Selenium
MICROSOFT_EMAIL = os.getenv("MICROSOFT_EMAIL", "")
MICROSOFT_PASSWORD = os.getenv("MICROSOFT_PASSWORD", "")
ENABLE_HEADLESS_AUTH = os.getenv("ENABLE_HEADLESS_AUTH", "false").lower() in ("true", "1", "yes")
