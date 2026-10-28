import os
import time
import random
import logging
from datetime import datetime
from django.utils import timezone
from .models import CompanySymbol, ErrorLog, ScreenerDownloadLog
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from webdriver_manager.chrome import ChromeDriverManager


# =====================================================
# LOGGING
# =====================================================

log = logging.getLogger("screener_downloader")
log.setLevel(logging.INFO)

if not log.handlers:
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    log.addHandler(console)

    file_handler = logging.FileHandler(
        "screener_download.log",
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)


# =====================================================
# ERROR LOGGING
# ErrorLog has no field for storing the error message.
# Detailed reasons are therefore kept in the file log
# and in the job's returned failed list.
# =====================================================

def log_screener_error(symbol, company_name=None, reason=None):
    log.error(
        "Screener download failed | Company: %s | Symbol: %s | Reason: %s",
        company_name or "Unknown",
        symbol,
        reason or "Unknown error",
    )

    try:
        ErrorLog.objects.create(
            error_type="SCREENER_DOWNLOAD_FAILED",
            equity_symbol=symbol,
            company_name=company_name,
            source="Screener Download",
        )
    except Exception:
        log.exception(
            "Could not save ErrorLog entry for symbol %s",
            symbol,
        )


# =====================================================
# COMPANY LOOKUP
# =====================================================

def get_company_name(symbol):
    company = CompanySymbol.objects.filter(
        symbol__iexact=symbol
    ).first()

    if not company:
        return None

    return company.company_name or company.name


# =====================================================
# CHROME DRIVER
# =====================================================

def create_driver(download_dir, user_data_dir=None, headless=False):
    os.makedirs(download_dir, exist_ok=True)
    download_dir = os.path.abspath(download_dir)

    options = Options()

    preferences = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }

    options.add_experimental_option("prefs", preferences)
    options.add_argument("--window-size=1920,1080")

    if user_data_dir:
        user_data_dir = os.path.abspath(
            os.path.expandvars(os.path.expanduser(user_data_dir))
        )

        if not os.path.isdir(user_data_dir):
            raise ValueError(
                "CHROME_PROFILE_NOT_FOUND: The selected Chrome profile "
                "folder does not exist: " + user_data_dir
            )

        options.add_argument(
            "--user-data-dir=" + user_data_dir
        )

    if headless:
        options.add_argument("--headless=new")

    service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(
        service=service,
        options=options,
    )

    # Explicitly enable downloads in Chrome's newer headless mode.
    if headless:
        try:
            driver.execute_cdp_cmd(
                "Page.setDownloadBehavior",
                {
                    "behavior": "allow",
                    "downloadPath": download_dir,
                },
            )
        except Exception:
            log.warning(
                "Could not set Chrome's download behavior through CDP."
            )

    return driver


# =====================================================
# LOGIN CHECK
# =====================================================

def ensure_screener_login(driver, timeout=600):
    """
    Open Screener in visible Chrome and wait for the user to log in manually.
    Continue only after the login page has been left successfully.
    """
    print("\n" + "=" * 60)
    print("SCREENER LOGIN REQUIRED")
    print("Enter your username and password in the Chrome window.")
    print("Complete any verification and click Login.")
    print("Downloads will begin automatically after login succeeds.")
    print("=" * 60 + "\n")

    deadline = time.time() + timeout
    login_form_seen = False

    while time.time() < deadline:
        try:
            current_url = driver.current_url.lower()

            password_fields = driver.find_elements(
                By.CSS_SELECTOR,
                "input[type='password']"
            )

            password_visible = any(
                field.is_displayed()
                for field in password_fields
            )

            if password_visible:
                login_form_seen = True

            # Wait until a login form has appeared and then disappeared.
            # Also verify that the browser has left the login URL.
            if (
                login_form_seen
                and not password_visible
                and "login" not in current_url
            ):
                print("Screener login appears successful.")
                print("Starting company downloads now...\n")
                return True

        except Exception as exc:
            print(f"Waiting for Screener login: {exc}")

        time.sleep(1)

    raise TimeoutError(
        "Screener login was not completed within 10 minutes. "
        "Please check the Chrome window and try again."
    )

def login_screener(driver, email, password, timeout=20):
    """
    Optional credential-based login for users who are not using
    an existing Chrome profile.
    """

    if not email or not password:
        raise ValueError(
            "SCREENER_CREDENTIALS_MISSING: Provide a Screener login "
            "or use an authenticated Chrome profile."
        )

    log.info("Logging into Screener.in using supplied credentials.")

    driver.get("https://www.screener.in/login/")

    wait = WebDriverWait(driver, timeout)

    username_field = wait.until(
        EC.presence_of_element_located((By.NAME, "username"))
    )
    password_field = wait.until(
        EC.presence_of_element_located((By.NAME, "password"))
    )

    username_field.clear()
    username_field.send_keys(email)

    password_field.clear()
    password_field.send_keys(password)

    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Login')]")
        )
    ).click()

    try:
        WebDriverWait(driver, timeout).until(
            lambda browser: "/login" not in browser.current_url.lower()
        )
    except TimeoutException:
        raise RuntimeError(
            "SCREENER_LOGIN_FAILED: Screener did not complete login. "
            "Check the credentials or sign in manually."
        )

    log.info("Screener login completed.")


# =====================================================
# DOWNLOAD TRACKING
# =====================================================

def get_download_snapshot(download_dir):
    """
    Record the existing files before a download begins.
    This prevents an older Excel file being counted as a new download.
    """

    snapshot = {}

    for filename in os.listdir(download_dir):
        full_path = os.path.join(download_dir, filename)

        if not os.path.isfile(full_path):
            continue

        try:
            snapshot[filename] = (
                os.path.getmtime(full_path),
                os.path.getsize(full_path),
            )
        except OSError:
            continue

    return snapshot


def wait_for_download(
    download_dir,
    previous_snapshot=None,
    timeout=90,
):
    """
    Wait for a newly created or changed download to finish.

    Chrome temporary files such as .crdownload are ignored.
    The resulting file must remain unchanged across multiple checks.
    """

    if previous_snapshot is None:
        previous_snapshot = get_download_snapshot(download_dir)

    deadline = time.time() + timeout
    stable_file = None
    stable_count = 0

    while time.time() < deadline:
        candidates = []

        for filename in os.listdir(download_dir):
            if filename.lower().endswith(
                (".crdownload", ".tmp", ".part")
            ):
                continue

            full_path = os.path.join(download_dir, filename)

            if not os.path.isfile(full_path):
                continue

            try:
                current_state = (
                    os.path.getmtime(full_path),
                    os.path.getsize(full_path),
                )
            except OSError:
                continue

            previous_state = previous_snapshot.get(filename)

            # Only consider files created or modified after the
            # current download was initiated.
            if previous_state == current_state:
                continue

            candidates.append((full_path, current_state))

        if candidates:
            newest_path, newest_state = max(
                candidates,
                key=lambda item: item[1][0],
            )

            if newest_path == stable_file and newest_state == getattr(
                wait_for_download, "_last_state", None
            ):
                stable_count += 1
            else:
                stable_file = newest_path
                stable_count = 0

            wait_for_download._last_state = newest_state

            # Allow several checks for Chrome to finish writing.
            if stable_count >= 2 and newest_state[1] > 0:
                return newest_path

        else:
            stable_file = None
            stable_count = 0
            wait_for_download._last_state = None

        time.sleep(1)

    raise TimeoutError(
        "DOWNLOAD_TIMEOUT: No new completed file appeared within "
        f"{timeout} seconds."
    )


# =====================================================
# DATABASE LOGGING
# =====================================================

def log_to_db(file_path, status):
    ScreenerDownloadLog.objects.create(
        file_name=os.path.basename(file_path) if file_path else "",
        file_path=os.path.abspath(file_path) if file_path else "",
        status=status,
    )


# =====================================================
# DOWNLOAD ONE COMPANY
# =====================================================

def download_symbol(
    driver,
    symbol,
    download_dir,
    timeout=90,
):
    symbol = symbol.strip().upper()

    if not symbol:
        raise ValueError("EMPTY_SYMBOL: Company symbol is empty.")

    url = (
        "https://www.screener.in/company/"
        + symbol
        + "/consolidated/"
    )

    log.info("Opening Screener page for %s", symbol)

    driver.get(url)

    # Wait until the page has loaded enough to inspect.
    wait = WebDriverWait(driver, 20)

    try:
        export_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(., 'Export to Excel')]",
                )
            )
        )
    except TimeoutException:
        current_url = driver.current_url.lower()

        if "/login" in current_url:
            raise RuntimeError(
                "SCREENER_LOGIN_REQUIRED: Screener redirected to "
                "the login page. Sign in and retry."
            )

        raise RuntimeError(
            "EXPORT_BUTTON_NOT_FOUND: Screener did not show the "
            "Export to Excel button. The symbol may be invalid, "
            "the page may have changed, or access may be restricted."
        )

    # Take a snapshot immediately before clicking.
    previous_snapshot = get_download_snapshot(download_dir)

    driver.execute_script(
        "arguments[0].click();",
        export_button,
    )

    file_path = wait_for_download(
        download_dir,
        previous_snapshot=previous_snapshot,
        timeout=timeout,
    )

    log_to_db(file_path, "SUCCESS")

    log.info(
        "Downloaded %s to %s",
        symbol,
        os.path.basename(file_path),
    )

    return file_path


# =====================================================
# MAIN ENTRY
# =====================================================
def download_for_symbols(
    symbols,
    download_dir,
    email=None,
    password=None,
    user_data_dir=None,
    headless=False,
    delay_range=(6, 14),
    per_download_timeout=90,
):
    """
    Open Screener in Chrome, wait for manual login, then download
    exports for each supplied company symbol.

    Returns:
      {
        "success": [
          {
            "symbol": "...",
            "company_name": "...",
            "path": "...",
            "timestamp": "..."
          }
        ],
        "failed": [
          {
            "symbol": "...",
            "company_name": "...",
            "error": "...",
            "timestamp": "..."
          }
        ]
      }
    """

    os.makedirs(download_dir, exist_ok=True)

    # Normalize and de-duplicate symbols while preserving their order.
    normalized_symbols = []
    seen = set()

    for value in symbols:
        symbol = str(value or "").strip().upper()

        if symbol and symbol not in seen:
            normalized_symbols.append(symbol)
            seen.add(symbol)

    success = []
    failed = []
    driver = None

    try:
        driver = create_driver(
            download_dir=download_dir,
            user_data_dir=user_data_dir,
            headless=False,  # The user must be able to see and use Chrome.
        )

        # Open Screener and wait for the user to complete login manually.
        driver.get("https://www.screener.in/")
        ensure_screener_login(driver, timeout=600)

        # Do not start downloads until login has succeeded.
        for index, symbol in enumerate(normalized_symbols, 1):
            company_name = get_company_name(symbol)

            try:
                log.info(
                    "Downloading %s/%s: %s (%s)",
                    index,
                    len(normalized_symbols),
                    symbol,
                    company_name or "Unknown company",
                )

                file_path = download_symbol(
                    driver=driver,
                    symbol=symbol,
                    download_dir=download_dir,
                    timeout=per_download_timeout,
                )

                success.append({
                    "symbol": symbol,
                    "company_name": company_name or symbol,
                    "path": file_path,
                    "timestamp": timezone.now().isoformat(),
                })

            except Exception as exc:
                reason = str(exc) or exc.__class__.__name__

                log_screener_error(
                    symbol=symbol,
                    company_name=company_name,
                    reason=reason,
                )

                failed.append({
                    "symbol": symbol,
                    "company_name": company_name or symbol,
                    "error": reason,
                    "timestamp": timezone.now().isoformat(),
                })

                log.exception(
                    "Download failed for %s (%s)",
                    symbol,
                    company_name or "Unknown company",
                )

            if index < len(normalized_symbols):
                delay = random.uniform(*delay_range)

                if index % 10 == 0:
                    delay += random.uniform(5, 20)

                time.sleep(delay)

    except Exception as exc:
        # If login or browser setup fails, record the reason rather than
        # silently returning an apparently successful job.
        reason = str(exc) or exc.__class__.__name__
        log.exception("Screener automation could not start: %s", reason)

        if not success and not failed:
            for symbol in normalized_symbols:
                failed.append({
                    "symbol": symbol,
                    "company_name": get_company_name(symbol) or symbol,
                    "error": reason,
                    "timestamp": timezone.now().isoformat(),
                })

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                log.exception("Error while closing Chrome.")

        log.info(
            "Screener job finished. Success: %s; Failed: %s",
            len(success),
            len(failed),
        )

    return {
        "success": success,
        "failed": failed,
    }