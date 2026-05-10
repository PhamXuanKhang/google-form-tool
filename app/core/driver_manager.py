"""
Driver Manager

Resolves Chrome binary and ChromeDriver paths at runtime without hardcoded paths.

Resolution order
----------------
Chrome binary:
  1. CHROME_BINARY_PATH in .env  (explicit override)
  2. <app>/drivers/chrome/chrome.exe  (bundled / manually placed)
  3. Common Windows system installation paths
  4. None  →  Selenium picks up system default Chrome

ChromeDriver:
  1. CHROME_DRIVER_PATH in .env  (explicit override)
  2. <app>/drivers/chromedriver/chromedriver.exe  (bundled / manually placed)
  3. %APPDATA%/GoogleFormTool/drivers/chromedriver/chromedriver.exe
  4. Auto-download via webdriver-manager  →  saved to app-data drivers directory
  5. None  →  Selenium Manager handles it at runtime
"""

import os
import shutil
import sys
from pathlib import Path

from app.logging_config import logger
from config import Config

# Per-process cache so the (potentially slow) download only happens once.
_cache: dict[str, str | None] = {}


def _app_drivers_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "drivers"
    return Path(__file__).resolve().parents[2] / "drivers"


def _cache_drivers_root() -> Path:
    return Path(Config.DRIVERS_DIR)


def get_driver_diagnostics() -> dict[str, str]:
    return {
        "bundled_drivers_dir": str(_app_drivers_root()),
        "cache_drivers_dir": str(_cache_drivers_root()),
    }


def _win_chrome_candidates() -> list[Path]:
    """Return common Chrome/Chromium installation paths on Windows."""
    candidates: list[Path] = []
    for env_var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(env_var, "")
        if base:
            candidates += [
                Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(base) / "Chromium" / "Application" / "chrome.exe",
                Path(base) / "Google" / "Chrome Beta" / "Application" / "chrome.exe",
            ]
    return candidates


def get_chrome_binary(explicit: str | None = None) -> str | None:
    """Return the Chrome binary path to pass to Selenium Options.

    Returns None when Chrome should be auto-detected by Selenium.
    """
    cache_key = f"binary:{explicit}"
    if cache_key in _cache:
        return _cache[cache_key]

    result: str | None = None

    if explicit:
        result = explicit
        logger.info(f"ChromeBinary: using .env override → {result}")
    else:
        local = _app_drivers_root() / "chrome" / "chrome.exe"
        if local.exists():
            result = str(local)
            logger.info(f"ChromeBinary: found in drivers/ → {result}")
        else:
            for candidate in _win_chrome_candidates():
                if candidate.exists():
                    result = str(candidate)
                    logger.info(f"ChromeBinary: found system install → {result}")
                    break
            else:
                logger.info("ChromeBinary: not found locally — Selenium will auto-detect")

    _cache[cache_key] = result
    return result


def get_chromedriver_path(explicit: str | None = None, *, allow_download: bool = True) -> str | None:
    """Return the ChromeDriver executable path to pass to selenium Service."""
    cache_key = f"driver:{explicit}:download:{allow_download}"
    if cache_key in _cache:
        return _cache[cache_key]

    result: str | None = None
    bundled = _app_drivers_root() / "chromedriver" / "chromedriver.exe"
    cache_dir = _cache_drivers_root() / "chromedriver"
    cached = cache_dir / "chromedriver.exe"

    if explicit:
        result = explicit
        logger.info(f"ChromeDriver: using .env override → {result}")
    elif bundled.exists():
        result = str(bundled)
        logger.info(f"ChromeDriver: found bundled driver → {result}")
    elif cached.exists():
        result = str(cached)
        logger.info(f"ChromeDriver: found cached driver → {result}")
    elif allow_download:
        try:
            from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
            from webdriver_manager.core.driver_cache import DriverCacheManager  # type: ignore

            cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("ChromeDriver: not found locally — downloading via webdriver-manager...")
            cache_manager = DriverCacheManager(root_dir=str(_cache_drivers_root()))
            downloaded = ChromeDriverManager(cache_manager=cache_manager).install()
            shutil.copy2(downloaded, cached)
            result = str(cached)
            logger.info(f"ChromeDriver: downloaded and saved → {result}")
        except ImportError:
            logger.info("webdriver-manager not installed — Selenium Manager will handle ChromeDriver")
        except Exception as exc:
            logger.warning(f"ChromeDriver auto-download failed ({exc}) — Selenium Manager fallback")
    else:
        logger.info("ChromeDriver: no cached driver found — Selenium Manager fallback")

    _cache[cache_key] = result
    return result
