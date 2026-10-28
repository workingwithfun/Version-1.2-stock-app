# balance/utils.py
import os
import shutil
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

LOG_FILE = os.path.join(os.path.dirname(__file__), "screener_download_readable.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(message)s"
)

def log_download(file_path, replaced=False):
    file_name = os.path.basename(file_path)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    status = "REPLACED" if replaced else "NEW"
    logging.info(f"{file_name}\t{file_path}\t{timestamp}\t{status}")

def move_and_replace_file(temp_path, final_dir, original_name):
    os.makedirs(final_dir, exist_ok=True)
    final_path = os.path.join(final_dir, original_name)
    replaced = os.path.exists(final_path)
    if replaced:
        os.remove(final_path)
    shutil.move(temp_path, final_path)
    log_download(final_path, replaced=replaced)
    return final_path


import os
import time

def wait_for_download(download_dir, original_name, timeout=60):
    """
    Waits for a file to finish downloading in download_dir.
    Renames it to original_name and replaces existing file if needed.
    Returns final_path and replaced flag.
    """
    end_time = time.time() + timeout
    final_path = os.path.join(download_dir, original_name)
    replaced = os.path.exists(final_path)

    while time.time() < end_time:
        files = os.listdir(download_dir)
        for f in files:
            if f.endswith(".crdownload"):
                continue  # still downloading
            # Assume this is the downloaded file
            temp_path = os.path.join(download_dir, f)
            # Replace old file if exists
            if replaced:
                os.remove(final_path)
            os.rename(temp_path, final_path)
            return final_path, replaced
        time.sleep(0.5)
    raise TimeoutError(f"File {original_name} not downloaded in {timeout} seconds")

def get_chrome_driver(download_dir, user_data_dir=None, headless=False):
    os.makedirs(download_dir, exist_ok=True)
    chrome_options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": os.path.abspath(download_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    if user_data_dir:
        chrome_options.add_argument(f"user-data-dir={os.path.abspath(user_data_dir)}")
    if headless:
        chrome_options.add_argument("--headless=new")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)
