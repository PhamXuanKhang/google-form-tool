# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Google Form Automation Tool
# Build: pyinstaller google_form_tool.spec --clean

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
console_enabled = os.environ.get("GOOGLE_FORM_TOOL_CONSOLE", "1") != "0"

# Babel locale data is large but required for Flask-Babel i18n
babel_datas = collect_data_files("babel", includes=["**/*.dat", "**/*.txt", "**/*.py"])
flask_babel_datas = collect_data_files("flask_babel")

# Bundle Selenium Manager so it can auto-download ChromeDriver at runtime
import selenium as _sel
_sel_mgr = Path(_sel.__file__).parent / "webdriver" / "common" / "windows" / "selenium-manager.exe"
selenium_binaries = (
    [(str(_sel_mgr), "selenium/webdriver/common/windows")] if _sel_mgr.exists() else []
)

a = Analysis(
    ["wsgi.py"],
    pathex=["."],
    binaries=selenium_binaries,
    datas=[
        ("app/templates",    "app/templates"),
        ("app/static",       "app/static"),
        ("app/translations", "app/translations"),
    ] + babel_datas + flask_babel_datas,
    hiddenimports=[
        # TinyDB
        "tinydb",
        "tinydb.storages",
        "tinydb.middlewares",
        # Pydantic
        "pydantic",
        "pydantic.v1",
        "pydantic.deprecated.class_validators",
        # Flask-Babel / Babel
        "flask_babel",
        "babel",
        "babel.dates",
        "babel.numbers",
        "babel.plural",
        # Waitress
        "waitress",
        "waitress.task",
        "waitress.server",
        "waitress.runner",
        # psutil
        "psutil",
        # openpyxl
        "openpyxl",
        "openpyxl.styles",
        "openpyxl.utils",
        # Selenium
        "selenium",
        "selenium.webdriver",
        "selenium.webdriver.chrome",
        "selenium.webdriver.chrome.options",
        "selenium.webdriver.chrome.service",
        "selenium.webdriver.common.by",
        "selenium.webdriver.support.ui",
        "selenium.webdriver.support.expected_conditions",
        # Google Generative AI (optional feature)
        "google.genai",
        # webdriver-manager (auto-downloads ChromeDriver)
        "webdriver_manager",
        "webdriver_manager.chrome",
        "webdriver_manager.core",
        "webdriver_manager.core.driver",
        "webdriver_manager.core.manager",
        "webdriver_manager.core.os_manager",
        "webdriver_manager.core.download_manager",
        "webdriver_manager.core.http",
        # App modules
        "app",
        "app.main_routes",
        "app.core.driver_manager",
        "app.models",
        "app.utils",
        "app.logging_config",
        "app.core",
        "app.core.form_extractor",
        "app.core.form_submitter",
        "app.core.form_processor",
        "app.core.ai_responder",
        "app.core.prefill_link_generator",
        "app.services",
        "app.services.storage_service",
        "app.monitoring",
        "app.monitoring.metrics_collector",
        "app.monitoring.cpu_monitor",
        "app.monitoring.network_monitor",
        "app.monitoring.thread_monitor",
        # Misc runtime deps
        "email.mime.multipart",
        "email.mime.text",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "_pytest", "unittest", "test"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GoogleFormTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # Disabled — UPX can trigger antivirus false positives
    console=console_enabled,
    icon="app/static/images/app_icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GoogleFormTool",
)
