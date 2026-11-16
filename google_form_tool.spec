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
        ("skills/google-form-automation/SKILL.md", "skills/google-form-automation"),
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
        "app.factory",
        "app.routes",
        "app.routes.health",
        "app.routes.pages",
        "app.routes.forms",
        "app.routes.data",
        "app.routes.ai",
        "app.routes.submissions",
        "app.routes.history",
        "app.routes.runs",
        "app.routes.templates",
        "app.models",
        "app.utils",
        "app.config",
        "app.logging_config",
        "app.domain",
        "app.domain.form_processor",
        "app.domain.prefill_link_generator",
        "app.domain.form_copy_planner",
        "app.mcp_server",
        "app.domain.response_plan",
        "app.domain.run_report",
        "app.domain.distribution_presets",
        "app.domain.config_template",
        "app.adapters",
        "app.adapters.browser",
        "app.adapters.browser.driver_manager",
        "app.adapters.browser.form_extractor",
        "app.adapters.browser.form_submitter",
        "app.adapters.browser.form_copier",
        "app.adapters.ai",
        "app.adapters.ai.ai_responder",
        "app.services",
        "app.services.storage_service",
        "app.services.upload_cache",
        "app.services.submission_manager",
        "app.services.history_export",
        "app.services.run_store",
        "app.services.template_store",
        "app.runtime_info",
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

# MCP server: a second, always-console exe in the same folder. It speaks MCP
# over stdin/stdout, so it cannot share the backend exe, whose console flag is
# fixed at build time. It only needs the HTTP proxy, not Flask or Selenium.
mcp_analysis = Analysis(
    ["mcp_server_entry.py"],
    pathex=["."],
    binaries=[],
    datas=collect_data_files("jsonschema_specifications"),
    hiddenimports=["app.mcp_server", "app.runtime_info", "app.config"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "_pytest", "unittest", "test", "flask", "selenium", "tinydb"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

mcp_pyz = PYZ(mcp_analysis.pure, mcp_analysis.zipped_data, cipher=block_cipher)

mcp_exe = EXE(
    mcp_pyz,
    mcp_analysis.scripts,
    [],
    exclude_binaries=True,
    name="GoogleFormToolMcp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon="app/static/images/app_icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    mcp_exe,
    mcp_analysis.binaries,
    mcp_analysis.zipfiles,
    mcp_analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GoogleFormTool",
)
