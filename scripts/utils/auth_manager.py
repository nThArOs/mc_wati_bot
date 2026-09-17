# ============================================================
# LIBRARIES
# ============================================================

import base64
import hashlib
import hmac
import json
import os
import struct
import sys
import threading
import time
import webbrowser
from simple_chalk import chalk

# Chargement facultatif des variables d'environnement
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


# ============================================================
# TOTP MANAGER (RFC 6238)
# ============================================================

class TOTPManager:
    """Générateur et vérificateur de jetons 2FA (TOTP - RFC 6238).

    Permet de générer des codes d'authentification temporaires à 6 chiffres
    compatibles avec Microsoft Authenticator / Google Authenticator.
    Fonctionne de manière autonome sans dépendance externe obligatoire
    (utilise pyotp s'il est installé, sinon implémentation native).
    """

    def __init__(self, secret=None, digits=6, interval=30):
        self.digits = digits
        self.interval = interval
        self.secret = self._clean_secret(secret) if secret else None

    @staticmethod
    def _clean_secret(secret):
        if not secret:
            return ""
        return str(secret).replace(" ", "").replace("-", "").strip().upper()

    def set_secret(self, secret):
        self.secret = self._clean_secret(secret)

    def is_configured(self):
        return bool(self.secret)

    def generate_code(self, secret=None, timestamp=None):
        active_secret = self._clean_secret(secret) if secret else self.secret
        if not active_secret:
            return None, 0

        ts = int(time.time() if timestamp is None else timestamp)
        remaining = self.interval - (ts % self.interval)

        # Utilisation de pyotp si la bibliothèque est présente
        try:
            import pyotp

            totp = pyotp.TOTP(
                active_secret,
                digits=self.digits,
                interval=self.interval,
            )
            return totp.at(ts), remaining
        except ImportError:
            pass

        # Implémentation native standard RFC 6238 (HMAC-SHA1)
        try:
            padding_needed = (8 - len(active_secret) % 8) % 8
            padded_secret = active_secret + ("=" * padding_needed)
            key = base64.b32decode(padded_secret, casefold=True)

            counter = ts // self.interval
            msg = struct.pack(">Q", counter)
            digest = hmac.new(key, msg, hashlib.sha1).digest()

            offset = digest[-1] & 0x0F
            binary = (
                struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
            )
            code = str(binary % (10 ** self.digits)).zfill(self.digits)
            return code, remaining
        except Exception:
            return None, 0

    def verify_code(self, code, secret=None, window=1):
        if not code:
            return False

        active_secret = self._clean_secret(secret) if secret else self.secret
        if not active_secret:
            return False

        code_str = str(code).strip()
        ts = int(time.time())

        for offset in range(-window, window + 1):
            check_time = ts + (offset * self.interval)
            expected, _ = self.generate_code(active_secret, timestamp=check_time)
            if expected and expected == code_str:
                return True

        return False

    def format_status(self):
        if not self.is_configured():
            return chalk.gray("Non configuré (aucun secret TOTP fourni)")

        code, remaining = self.generate_code()
        if not code:
            return chalk.red("Clé secrète TOTP invalide")

        color = chalk.green if remaining > 10 else chalk.yellow
        return f"{chalk.cyanBright(code)} {color(f'({remaining}s restantes)')}"


# ============================================================
# TOKEN CACHE MANAGER
# ============================================================

class TokenManager:
    """Gestionnaire de persistance des jetons OAuth Microsoft.

    Isole le stockage des Refresh Tokens et jetons de session
    par instance de bot dans le dossier spécifié (ex: ./tokens/<bot_name>).
    """

    def __init__(self, bot_name="default", base_dir="./tokens"):
        self.bot_name = bot_name
        self.base_dir = os.path.abspath(base_dir)
        self.profile_dir = os.path.join(self.base_dir, bot_name)
        self.ensure_directory()

    def ensure_directory(self):
        os.makedirs(self.profile_dir, exist_ok=True)
        return self.profile_dir

    def get_profile_path(self):
        return self.profile_dir

    def list_token_files(self):
        if not os.path.exists(self.profile_dir):
            return []

        token_files = []
        for root, _, files in os.walk(self.profile_dir):
            for filename in files:
                if filename.endswith(".json"):
                    full_path = os.path.join(root, filename)
                    try:
                        stat = os.stat(full_path)
                        token_files.append({
                            "name": filename,
                            "path": full_path,
                            "size": stat.st_size,
                            "mtime": stat.st_mtime,
                        })
                    except OSError:
                        pass
        return token_files

    def has_cached_tokens(self):
        files = self.list_token_files()
        for f in files:
            if f["size"] > 0:
                return True
        return False

    def get_token_summary(self):
        files = self.list_token_files()
        has_tokens = any(f["size"] > 0 for f in files)

        account_hint = None
        for f in files:
            try:
                with open(f["path"], "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    if isinstance(data, dict):
                        for key in ("username", "email", "name", "gamertag"):
                            if key in data and isinstance(data[key], str):
                                account_hint = data[key]
                                break
            except Exception:
                pass

        last_modified = max((f["mtime"] for f in files), default=None)
        last_modified_str = (
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_modified))
            if last_modified
            else "Aucun"
        )

        return {
            "bot_name": self.bot_name,
            "profile_dir": self.profile_dir,
            "has_tokens": has_tokens,
            "file_count": len(files),
            "files": [f["name"] for f in files],
            "last_modified": last_modified_str,
            "account_hint": account_hint,
        }

    def clear_tokens(self):
        files = self.list_token_files()
        deleted_count = 0
        for f in files:
            try:
                os.remove(f["path"])
                deleted_count += 1
            except OSError:
                pass
        return deleted_count


# ============================================================
# AUTOMATED AUTH LOGIN (HEADLESS SELENIUM)
# ============================================================

class AutomatedAuthLogin:
    """Automatisation sans tête (headless) de la validation Device Code et 2FA.

    Permet de valider automatiquement le formulaire Microsoft et le code
    TOTP en arrière-plan lorsque les identifiants sont fournis.
    """

    @staticmethod
    def start_headless_login(
        verification_uri,
        user_code,
        email,
        password,
        totp_manager=None,
        logger=None,
    ):
        def _login_task():
            log = logger or (lambda msg: print(f"[AuthAuto] {msg}"))
            try:
                from selenium import webdriver
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.chrome.options import Options

                options = Options()
                options.add_argument("--headless=new")
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--window-size=1920,1080")

                log(chalk.cyan("Démarrage du navigateur headless pour authentification..."))
                driver = webdriver.Chrome(options=options)
                wait = WebDriverWait(driver, 15)

                try:
                    # 1. Page Device Login & Code
                    driver.get(verification_uri)
                    code_input = wait.until(
                        EC.element_to_be_clickable((By.ID, "otc"))
                    )
                    code_input.clear()
                    code_input.send_keys(user_code)
                    
                    next_btn = driver.find_element(By.ID, "idSIButton9")
                    next_btn.click()
                    time.sleep(2)

                    # 2. Saisie de l'email
                    if email:
                        email_input = wait.until(
                            EC.element_to_be_clickable((By.NAME, "loginfmt"))
                        )
                        email_input.clear()
                        email_input.send_keys(email)
                        driver.find_element(By.ID, "idSIButton9").click()
                        time.sleep(2)

                    # 3. Saisie du mot de passe
                    if password:
                        pwd_input = wait.until(
                            EC.element_to_be_clickable((By.NAME, "passwd"))
                        )
                        pwd_input.clear()
                        pwd_input.send_keys(password)
                        driver.find_element(By.ID, "idSIButton9").click()
                        time.sleep(3)

                    # 4. Gestion du 2FA / TOTP si demandé
                    if totp_manager and totp_manager.is_configured():
                        try:
                            totp_code, _ = totp_manager.generate_code()
                            totp_input = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.ID, "idTxtBx_SAOTCC_OTC"))
                            )
                            totp_input.clear()
                            totp_input.send_keys(totp_code)
                            driver.find_element(By.ID, "idSubmit_SAOTCC_Continue").click()
                            time.sleep(2)
                        except Exception:
                            pass

                    # 5. Validation finale ("Rester connecté" / Autoriser)
                    try:
                        accept_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.ID, "idSIButton9"))
                        )
                        accept_btn.click()
                        time.sleep(2)
                    except Exception:
                        pass

                    log(chalk.green("✓ Authentification headless validée avec succès !"))

                finally:
                    driver.quit()

            except Exception as e:
                if logger:
                    logger(
                        chalk.yellow(
                            f"Authentification automatique incomplète ({e}). "
                            f"Veuillez valider manuellement via le lien et code affichés."
                        )
                    )

        threading.Thread(target=_login_task, daemon=True).start()


# ============================================================
# MFA DEVICE CODE HANDLER
# ============================================================

class MfaDeviceCodeHandler:
    """Gestionnaire d'événements de connexion Device Code Microsoft (2FA).

    Intercepte le callback onMsaCode de Mineflayer / prismarine-auth,
    affiche les instructions de validation 2FA en console avec simple_chalk,
    génère le jeton TOTP si configuré et ouvre la page dans le navigateur.
    """

    def __init__(
        self,
        bot_name,
        totp_manager=None,
        auto_open_browser=True,
        logger=None,
        headless_email=None,
        headless_password=None,
        enable_headless=False,
    ):
        self.bot_name = bot_name
        self.totp_manager = totp_manager or TOTPManager()
        self.auto_open_browser = auto_open_browser
        self.logger = logger or (lambda msg: print(f"[{bot_name}] {msg}"))
        self.headless_email = headless_email
        self.headless_password = headless_password
        self.enable_headless = enable_headless
        self.last_code_info = None

    def _safe_get(self, obj, key, default=""):
        try:
            val = getattr(obj, key, None)
            if val is not None:
                return str(val)
        except Exception:
            pass
        try:
            val = obj[key]
            if val is not None:
                return str(val)
        except Exception:
            pass
        return default

    def on_msa_code(self, data):
        user_code = self._safe_get(data, "user_code")
        verification_uri = self._safe_get(
            data,
            "verification_uri",
            "https://microsoft.com/devicelogin",
        )
        expires_in = self._safe_get(data, "expires_in", "900")

        self.last_code_info = {
            "user_code": user_code,
            "verification_uri": verification_uri,
            "expires_in": expires_in,
            "received_at": time.time(),
        }

        print()
        print(chalk.yellow("=" * 60))
        print(chalk.cyanBright(" DOUBLE AUTHENTIFICATION MICROSOFT (2FA / JETON)"))
        print(chalk.yellow("=" * 60))
        self.logger(
            chalk.white(
                "Une validation double facteur est requise pour connecter le bot."
            )
        )
        self.logger(
            chalk.cyan(
                f"1. Ouvrez l'URL : {verification_uri}"
            )
        )
        self.logger(
            chalk.greenBright(
                f"2. Saisissez le code : {user_code}"
            )
        )
        self.logger(
            chalk.gray(
                f"3. Validez l'accès sur Microsoft (expire dans {expires_in}s)."
            )
        )

        if self.totp_manager and self.totp_manager.is_configured():
            code, remaining = self.totp_manager.generate_code()
            if code:
                color = chalk.green if remaining > 10 else chalk.yellow
                self.logger(
                    chalk.magenta(
                        f"4. Jeton 2FA TOTP généré : {code} "
                    )
                    + color(f"({remaining}s restantes)")
                )

        print(chalk.yellow("=" * 60))
        print()

        # Automatisation sans tête si activée et identifiants disponibles
        if self.enable_headless and self.headless_email and self.headless_password:
            AutomatedAuthLogin.start_headless_login(
                verification_uri=verification_uri,
                user_code=user_code,
                email=self.headless_email,
                password=self.headless_password,
                totp_manager=self.totp_manager,
                logger=self.logger,
            )
        elif self.auto_open_browser and verification_uri:
            try:
                self.logger(
                    chalk.cyan(
                        "Ouverture de la page de validation dans le navigateur..."
                    )
                )
                webbrowser.open(verification_uri)
            except Exception as e:
                self.logger(
                    chalk.gray(
                        f"Impossible d'ouvrir le navigateur automatique: {e}"
                    )
                )
