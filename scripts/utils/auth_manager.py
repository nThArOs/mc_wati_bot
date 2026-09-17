# ============================================================
# LIBRARIES
# ============================================================

import base64
import hashlib
import hmac
import json
import os
import re
import shutil
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
        self.expected_hash = hashlib.sha1(bot_name.encode("utf-8")).hexdigest()[:6]
        self.ensure_directory()
        self._check_and_migrate_legacy_cache()
        self._align_cache_hash_prefixes()

    def _align_cache_hash_prefixes(self):
        """Assure que les fichiers de cache portent le préfixe de hash sha1 attendu
        par prismarine-auth (crypto.createHash('sha1').update(username).digest('hex')[:6]).
        Si des fichiers valides existent avec un autre préfixe (ex: suite à migration),
        ils sont synchronisés sous le préfixe cible.
        """
        if not os.path.exists(self.profile_dir):
            return

        try:
            files = os.listdir(self.profile_dir)
        except OSError:
            return

        valid_cache_by_type = {}
        for fname in files:
            if not fname.endswith(".json"):
                continue
            fp = os.path.join(self.profile_dir, fname)
            try:
                if os.path.getsize(fp) > 10:
                    m = re.match(r"^[a-f0-9]{6}_(.*)$", fname)
                    if m:
                        cache_type = m.group(1)
                        if cache_type not in valid_cache_by_type:
                            valid_cache_by_type[cache_type] = fp
            except OSError:
                continue

        for cache_type, valid_fp in valid_cache_by_type.items():
            target_name = f"{self.expected_hash}_{cache_type}"
            target_path = os.path.join(self.profile_dir, target_name)
            needs_copy = False
            if not os.path.exists(target_path):
                needs_copy = True
            else:
                try:
                    if os.path.getsize(target_path) <= 10:
                        needs_copy = True
                except OSError:
                    needs_copy = True

            if needs_copy and os.path.abspath(valid_fp) != os.path.abspath(target_path):
                try:
                    shutil.copy2(valid_fp, target_path)
                except Exception:
                    pass

    def _check_and_migrate_legacy_cache(self):
        """Si le dossier de jetons est vide, tente d'importer les jetons existants
        depuis un autre profil (ex: pathfinder-bot) dont le compte correspond à ce bot.
        """
        if self.has_cached_tokens():
            return

        if not os.path.exists(self.base_dir):
            return

        for item in os.listdir(self.base_dir):
            candidate_dir = os.path.join(self.base_dir, item)
            if not os.path.isdir(candidate_dir) or candidate_dir == self.profile_dir:
                continue

            candidate_files = []
            try:
                for f in os.listdir(candidate_dir):
                    if f.endswith(".json"):
                        fp = os.path.join(candidate_dir, f)
                        if os.path.getsize(fp) > 10:
                            candidate_files.append((f, fp))
            except OSError:
                continue

            if not candidate_files:
                continue

            # Vérifier si l'un des fichiers contient le nom du bot
            matched = False
            for fname, fpath in candidate_files:
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                        content = fp.read()
                        if self.bot_name.lower() in content.lower():
                            matched = True
                            break
                except Exception:
                    pass

            if matched:
                for fname, fpath in candidate_files:
                    dst = os.path.join(self.profile_dir, fname)
                    try:
                        shutil.copy2(fpath, dst)
                    except Exception:
                        pass
                    m = re.match(r"^[a-f0-9]{6}_(.*)$", fname)
                    if m:
                        dst_aligned = os.path.join(
                            self.profile_dir, f"{self.expected_hash}_{m.group(1)}"
                        )
                        try:
                            shutil.copy2(fpath, dst_aligned)
                        except Exception:
                            pass
                break

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
        self._align_cache_hash_prefixes()
        files = self.list_token_files()
        for f in files:
            if f["size"] > 10 and f["name"].startswith(f"{self.expected_hash}_"):
                return True
        for f in files:
            if f["size"] > 10:
                return True
        return False

    def get_token_summary(self):
        self._align_cache_hash_prefixes()
        files = self.list_token_files()
        has_tokens = self.has_cached_tokens()

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
            "expected_hash": self.expected_hash,
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
# AUTOMATED AUTH LOGIN (SELENIUM AUTO-FILLER)
# ============================================================

class AutomatedAuthLogin:
    """Automatisation de la validation Device Code et 2FA avec Selenium.

    Ouvre une fenêtre de navigateur Chrome, saisit automatiquement le code
    de validation Microsoft, clique sur 'Suivant', et pré-remplit les
    identifiants et le jeton 2FA TOTP si configurés.
    """

    @staticmethod
    def copy_to_clipboard(text):
        """Copie le code dans le presse-papiers du système."""
        try:
            import subprocess

            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"Set-Clipboard -Value '{text}'",
                ],
                capture_output=True,
                check=False,
            )
        except Exception:
            pass

    @staticmethod
    def start_browser_login(
        verification_uri,
        user_code,
        email=None,
        password=None,
        totp_manager=None,
        headless=False,
        logger=None,
    ):
        def _login_task():
            log = logger or (lambda msg: print(f"[AuthAuto] {msg}"))
            try:
                from selenium import webdriver
                from selenium.webdriver.common.by import By
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.chrome.options import Options

                options = Options()
                if headless:
                    options.add_argument("--headless=new")
                    options.add_argument("--disable-gpu")
                else:
                    options.add_experimental_option("detach", True)
                    options.add_argument("--start-maximized")

                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-notifications")

                log(chalk.cyan("Ouverture automatique de Chrome via Selenium..."))
                driver = webdriver.Chrome(options=options)
                wait = WebDriverWait(driver, 15)

                def safe_click(elem):
                    if not elem:
                        return False
                    try:
                        target = elem
                        try:
                            clickable_parent = elem.find_element(
                                By.XPATH,
                                "./ancestor-or-self::*[@role='button' or self::button or self::a or contains(@class, 'tile') or contains(@class, 'row') or contains(@class, 'table')][1]",
                            )
                            if clickable_parent:
                                target = clickable_parent
                        except Exception:
                            pass

                        try:
                            target.click()
                            return True
                        except Exception:
                            pass

                        driver.execute_script("arguments[0].click();", target)
                        return True
                    except Exception:
                        return False

                try:
                    # 1. Chargement de la page et saisie du code de liaison
                    driver.get(verification_uri)
                    log(
                        chalk.cyan(
                            f"Saisie automatique du code Microsoft : {user_code}..."
                        )
                    )

                    code_input = wait.until(
                        EC.element_to_be_clickable((By.ID, "otc"))
                    )
                    code_input.clear()
                    code_input.send_keys(user_code)

                    next_btn = wait.until(
                        EC.element_to_be_clickable((By.ID, "idSIButton9"))
                    )
                    next_btn.click()

                    log(
                        chalk.green(
                            f"✓ Code {user_code} saisi et validé automatiquement dans le navigateur !"
                        )
                    )
                    time.sleep(2)

                    # Boucle adaptative de validation des étapes Microsoft
                    start_time = time.time()
                    timeout = 90
                    email_submitted = not bool(email)
                    password_submitted = not bool(password)
                    totp_submitted = not (
                        totp_manager and totp_manager.is_configured()
                    )

                    log(
                        chalk.cyan(
                            "Suivi adaptatif des étapes Microsoft (email / mot de passe / 2FA / consentement)..."
                        )
                    )

                    while time.time() - start_time < timeout:
                        time.sleep(1.2)

                        # A. Écran de sélection de compte (tuile existante)
                        if email and not email_submitted:
                            try:
                                tiles = driver.find_elements(
                                    By.XPATH,
                                    f"//*[contains(text(), '{email}')]",
                                )
                                for t in tiles:
                                    if t.is_displayed():
                                        if safe_click(t):
                                            log(
                                                chalk.green(
                                                    f"✓ Compte {email} sélectionné dans la liste."
                                                )
                                            )
                                            email_submitted = True
                                            time.sleep(1.5)
                                            break
                            except Exception:
                                pass

                        # B. Saisie de l'adresse email
                        if email and not email_submitted:
                            try:
                                email_inputs = driver.find_elements(
                                    By.CSS_SELECTOR,
                                    "input[name='loginfmt'], #i0116, input[type='email'], input[name='username']",
                                )
                                for inp in email_inputs:
                                    if inp.is_displayed() and inp.is_enabled():
                                        inp.clear()
                                        inp.send_keys(email)
                                        time.sleep(0.5)
                                        try:
                                            btn = driver.find_element(
                                                By.ID, "idSIButton9"
                                            )
                                            if btn.is_displayed() and btn.is_enabled():
                                                btn.click()
                                            else:
                                                inp.send_keys(Keys.ENTER)
                                        except Exception:
                                            inp.send_keys(Keys.ENTER)

                                        log(
                                            chalk.green(
                                                f"✓ Email {email} renseigné et validé."
                                            )
                                        )
                                        email_submitted = True
                                        time.sleep(2)
                                        break
                            except Exception:
                                pass

                        # C. Saisie directe du mot de passe (si champ affiché à l'écran)
                        if password and not password_submitted:
                            try:
                                pwd_inputs = driver.find_elements(
                                    By.CSS_SELECTOR,
                                    "input[name='passwd'], #i0118, input[type='password']",
                                )
                                for inp in pwd_inputs:
                                    if inp.is_displayed() and inp.is_enabled():
                                        inp.clear()
                                        inp.send_keys(password)
                                        time.sleep(0.5)
                                        try:
                                            btn = driver.find_element(
                                                By.ID, "idSIButton9"
                                            )
                                            if btn.is_displayed() and btn.is_enabled():
                                                btn.click()
                                            else:
                                                inp.send_keys(Keys.ENTER)
                                        except Exception:
                                            inp.send_keys(Keys.ENTER)

                                        log(
                                            chalk.green(
                                                "✓ Mot de passe renseigné et validé."
                                            )
                                        )
                                        password_submitted = True
                                        time.sleep(2)
                                        break
                            except Exception:
                                pass

                        # D. Sélection de méthode de connexion (quand plusieurs choix sont proposés)
                        # Priorité 1 : "Utiliser votre mot de passe" si mot de passe configuré
                        if password and not password_submitted:
                            try:
                                pwd_candidates = driver.find_elements(
                                    By.XPATH,
                                    "//*[@role='button' or self::button or self::a or contains(@class, 'tile')][contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'mot de passe') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'password')]",
                                )
                                if not pwd_candidates:
                                    pwd_candidates = driver.find_elements(
                                        By.XPATH,
                                        "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'mot de passe') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'password') or @id='idA_PWD_SwitchToPassword']",
                                    )
                                for cand in pwd_candidates:
                                    if cand.is_displayed() and safe_click(cand):
                                        log(
                                            chalk.green(
                                                "✓ Option 'Utiliser votre mot de passe' sélectionnée."
                                            )
                                        )
                                        time.sleep(1.5)
                                        break
                            except Exception:
                                pass

                        # Priorité 2 : "Utiliser une application d'authentification" si mot de passe déjà saisi ou absent
                        elif (
                            totp_manager
                            and totp_manager.is_configured()
                            and not totp_submitted
                        ):
                            try:
                                app_candidates = driver.find_elements(
                                    By.XPATH,
                                    "//*[@role='button' or self::button or self::a or contains(@class, 'tile')][contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'application') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'authenticator')]",
                                )
                                if not app_candidates:
                                    app_candidates = driver.find_elements(
                                        By.XPATH,
                                        "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'application d’authentification') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), \"application d'authentification\") or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'code de vérification') or @data-value='PhoneAppOTP']",
                                    )
                                for cand in app_candidates:
                                    if cand.is_displayed() and safe_click(cand):
                                        log(
                                            chalk.green(
                                                "✓ Option 'Application d'authentification' sélectionnée."
                                            )
                                        )
                                        time.sleep(1.5)
                                        break
                            except Exception:
                                pass

                        # E. Écran "Autre méthode de connexion" / Dérivation si Microsoft attend une notification mobile
                        try:
                            alt_method_links = driver.find_elements(
                                By.CSS_SELECTOR,
                                "a#signInAnotherWay, a#idA_PWD_SwitchToCredPicker, a#idA_SAOTCS_AlternativeMethod, a#idA_SAOTCC_AlternativeMethod",
                            )
                            if not alt_method_links:
                                alt_method_links = driver.find_elements(
                                    By.XPATH,
                                    "//a[contains(text(), 'autrement') or contains(text(), 'autre méthode') or contains(text(), 'autres options') or contains(text(), 'autre option') or contains(text(), 'other ways') or contains(text(), 'Sign-in options') or contains(text(), 'Je ne peux pas utiliser') or contains(text(), 'options de connexion')]",
                                )
                            for link in alt_method_links:
                                if link.is_displayed() and link.is_enabled():
                                    if safe_click(link):
                                        log(
                                            chalk.cyan(
                                                "Sélection des autres options d'authentification..."
                                            )
                                        )
                                        time.sleep(1.5)
                                        break
                        except Exception:
                            pass

                        # F. Saisie directe du code 2FA / TOTP
                        if (
                            totp_manager
                            and totp_manager.is_configured()
                            and not totp_submitted
                        ):
                            try:
                                totp_inputs = driver.find_elements(
                                    By.CSS_SELECTOR,
                                    "#idTxtBx_SAOTCC_OTC, input[name='otc'], input[type='tel'], input[autocomplete='one-time-code']",
                                )
                                for inp in totp_inputs:
                                    if inp.is_displayed() and inp.is_enabled():
                                        code, rem = totp_manager.generate_code()
                                        inp.clear()
                                        inp.send_keys(code)
                                        time.sleep(0.5)
                                        sub_btns = driver.find_elements(
                                            By.CSS_SELECTOR,
                                            "#idSubmit_SAOTCC_Continue, #idSIButton9, input[type='submit']",
                                        )
                                        clicked = False
                                        for sb in sub_btns:
                                            if sb.is_displayed() and sb.is_enabled():
                                                sb.click()
                                                clicked = True
                                                break
                                        if not clicked:
                                            inp.send_keys(Keys.ENTER)

                                        log(
                                            chalk.green(
                                                f"✓ Jeton 2FA TOTP {code} renseigné et validé."
                                            )
                                        )
                                        totp_submitted = True
                                        time.sleep(2)
                                        break
                            except Exception:
                                pass

                        # G. Écran de consentement Minecraft ("Êtes-vous en train de vous connecter à Minecraft ?")
                        try:
                            consent_btns = driver.find_elements(
                                By.XPATH,
                                "//button[contains(text(), 'Continuer') or contains(text(), 'Continue') or contains(text(), 'Oui') or contains(text(), 'Yes') or contains(text(), 'Accepter') or contains(text(), 'Accept')] | //input[@type='submit' and (contains(@value, 'Continuer') or contains(@value, 'Continue') or contains(@value, 'Oui') or contains(@value, 'Yes'))]",
                            )
                            for cb in consent_btns:
                                if cb.is_displayed() and cb.is_enabled():
                                    cb.click()
                                    log(
                                        chalk.green(
                                            "✓ Écran de confirmation / consentement validé."
                                        )
                                    )
                                    time.sleep(2)
                                    break
                        except Exception:
                            pass

                        # H. Écran "Rester connecté ?" (KMSI)
                        try:
                            kmsi_btns = driver.find_elements(By.ID, "idSIButton9")
                            for b in kmsi_btns:
                                if b.is_displayed() and b.is_enabled():
                                    val = (
                                        b.get_attribute("value")
                                        or b.text
                                        or ""
                                    ).lower()
                                    if any(
                                        w in val
                                        for w in (
                                            "oui",
                                            "yes",
                                            "continuer",
                                            "continue",
                                            "suivant",
                                            "next",
                                        )
                                    ):
                                        b.click()
                                        log(
                                            chalk.green(
                                                "✓ Écran 'Rester connecté' validé."
                                            )
                                        )
                                        time.sleep(2)
                                        break
                        except Exception:
                            pass

                        # I. Vérification de succès (écran final)
                        try:
                            done_markers = driver.find_elements(
                                By.XPATH,
                                "//*[contains(text(), 'connecté') or contains(text(), 'All set') or contains(text(), 'terminé') or contains(text(), 'All done') or contains(text(), 'Tout est prêt')]",
                            )
                            if any(m.is_displayed() for m in done_markers):
                                log(
                                    chalk.green(
                                        "✓ Authentification Microsoft terminée avec succès !"
                                    )
                                )
                                break
                        except Exception:
                            pass

                    if headless:
                        log(chalk.green("✓ Authentification headless validée !"))
                    else:
                        log(
                            chalk.green(
                                "✓ Saisie terminée. La fenêtre Chrome reste ouverte pour vérification."
                            )
                        )

                finally:
                    if headless:
                        driver.quit()

            except Exception as e:
                log(
                    chalk.yellow(
                        f"Saisie Selenium non disponible ({e}). "
                        f"Ouverture classique du navigateur..."
                    )
                )
                try:
                    webbrowser.open(verification_uri)
                except Exception:
                    pass

        threading.Thread(target=_login_task, daemon=True).start()


# ============================================================
# MFA DEVICE CODE HANDLER
# ============================================================

class MfaDeviceCodeHandler:
    """Gestionnaire d'événements de connexion Device Code Microsoft (2FA).

    Intercepte le callback onMsaCode de Mineflayer / prismarine-auth,
    affiche les instructions 2FA, copie le code dans le presse-papiers
    et lance la saisie automatique via Selenium.
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

        # Copie automatique dans le presse-papiers
        AutomatedAuthLogin.copy_to_clipboard(user_code)
        self.logger(chalk.gray(f"Code {user_code} copié dans le presse-papiers."))

        # Saisie et validation automatique via Selenium
        if self.auto_open_browser and verification_uri:
            AutomatedAuthLogin.start_browser_login(
                verification_uri=verification_uri,
                user_code=user_code,
                email=self.headless_email,
                password=self.headless_password,
                totp_manager=self.totp_manager,
                headless=self.enable_headless,
                logger=self.logger,
            )


# ============================================================
# BOT CREDENTIALS RESOLVER
# ============================================================

def get_bot_credentials(bot_name):
    """Résout les identifiants Microsoft et clé secrète TOTP pour un bot donné.

    Priorités de recherche des variables d'environnement :
      1. Préfixe spécifique avec nom du bot (ex: NTHAROS_EMAIL, NTHAROS_PASSWORD)
      2. Préfixe spécifique alternatif (ex: MICROSOFT_EMAIL_NTHAROS)
      3. Variables génériques globales (MICROSOFT_EMAIL, MICROSOFT_MAIL, etc.)
    """
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

