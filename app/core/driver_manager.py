"""
Driver Manager

Resolves Chrome binary and ChromeDriver paths at runtime without hardcoded paths.

Resolution order
----------------
Chrome binary:
  1. CHROME_BINARY_PATH in .env  (explicit override)
  2. <base>/drivers/chrome/chrome.exe  (bundled / manually placed)
  3. Common Windows system installation paths
  4. None  →  Selenium picks up system default Chrome

ChromeDriver:
  1. CHROME_DRIVER_PATH in .env  (explicit override)
  2. <base>/drivers/chromedriver/chromedriver.exe  (previously downloaded or manual)
  3. Auto-download via webdriver-manager  →  saved to <base>/drivers/chromedriver/
  4. None  →  Selenium Manager handles it at runtime

<base> is the exe directory when frozen, project root in development.
"""

import os
import shutil
import sys
from pathlib import Path

from app.logging_config import logger

# Per-process cache so the (potentially slow) download only happens once.
_cache: dict[str, str | None] = {}


def _drivers_root() -> Path:
    """Return the persistent drivers/ base directory.

    - Frozen exe  → directory containing GoogleFormTool.exe
    - Development → project root (parent of app/)
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "drivers"
    # __file__ is app/core/driver_manager.py → parents[2] is project root
    return Path(__file__).resolve().parents[2] / "drivers"


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
        local = _drivers_root() / "chrome" / "chrome.exe"
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


def get_chromedriver_path(explicit: str | None = None) -> str | None:
    """Return the ChromeDriver executable path to pass to selenium Service.

    Auto-downloads via webdriver-manager on first call if not already present.
    Returns None only as a last resort (Selenium Manager will try to handle it).
    """
    cache_key = f"driver:{explicit}"
    if cache_key in _cache:
        return _cache[cache_key]

    result: str | None = None
    driver_dir = _drivers_root() / "chromedriver"
    local = driver_dir / "chromedriver.exe"

    if explicit:
        result = explicit
        logger.info(f"ChromeDriver: using .env override → {result}")
    elif local.exists():
        result = str(local)
        logger.info(f"ChromeDriver: found in drivers/ → {result}")
    else:
        # Auto-download and persist in drivers/chromedriver/
        try:
            from webdriver_manager.chrome import ChromeDriverManager  # type: ignore

            driver_dir.mkdir(parents=True, exist_ok=True)
            logger.info("ChromeDriver: not found locally — downloading via webdriver-manager...")
            downloaded = ChromeDriverManager().install()
            shutil.copy2(downloaded, local)
            result = str(local)
            logger.info(f"ChromeDriver: downloaded and saved → {result}")
        except ImportError:
            logger.info("webdriver-manager not installed — Selenium Manager will handle ChromeDriver")
        except Exception as exc:
            logger.warning(f"ChromeDriver auto-download failed ({exc}) — Selenium Manager fallback")

    _cache[cache_key] = result
    return result
