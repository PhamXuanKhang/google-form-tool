import app.main_routes as main_routes
from config import Config


def test_runtime_diagnostics_route_returns_paths_and_dev_mode(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_FORM_TOOL_ELECTRON", raising=False)
    monkeypatch.setattr(main_routes.sys, "frozen", False, raising=False)
    monkeypatch.setattr(main_routes, "get_chrome_binary", lambda explicit=None: r"C:\Chrome\chrome.exe")

    def fake_get_chromedriver_path(explicit=None, *, allow_download=True):
        assert allow_download is False
        return r"C:\Driver\chromedriver.exe"

    monkeypatch.setattr(main_routes, "get_chromedriver_path", fake_get_chromedriver_path)
    monkeypatch.setattr(
        main_routes,
        "get_driver_diagnostics",
        lambda: {"bundled_drivers_dir": r"C:\App\drivers", "cache_drivers_dir": r"C:\Data\drivers"},
    )

    response = client.get("/diagnostics/runtime")

    assert response.status_code == 200
    data = response.get_json()
    assert data["app_data_path"] == Config.APP_DATA_PATH
    assert data["db_path"] == Config.DB_PATH
    assert data["log_path"] == Config.LOG_DIR
    assert data["chrome_path"] == r"C:\Chrome\chrome.exe"
    assert data["chromedriver_path"] == r"C:\Driver\chromedriver.exe"
    assert data["bundled_drivers_dir"] == r"C:\App\drivers"
    assert data["cache_drivers_dir"] == r"C:\Data\drivers"
    assert data["mode"] == "dev"


def test_runtime_mode_uses_explicit_electron_marker(monkeypatch):
    monkeypatch.setenv("GOOGLE_FORM_TOOL_ELECTRON", "1")
    monkeypatch.setattr(main_routes.sys, "frozen", False, raising=False)

    assert main_routes._runtime_mode() == "electron"


def test_no_browser_marker_alone_is_not_electron(monkeypatch):
    monkeypatch.delenv("GOOGLE_FORM_TOOL_ELECTRON", raising=False)
    monkeypatch.setenv("GOOGLE_FORM_TOOL_NO_BROWSER", "1")
    monkeypatch.setattr(main_routes.sys, "frozen", False, raising=False)

    assert main_routes._runtime_mode() == "dev"


def test_settings_diagnostics_page_renders_runtime_paths(client, monkeypatch):
    monkeypatch.setattr(
        main_routes,
        "_runtime_diagnostics",
        lambda: {
            "app_data_path": r"C:\Data\GoogleFormTool",
            "db_path": r"C:\Data\GoogleFormTool\db.json",
            "log_path": r"C:\Data\GoogleFormTool\logs",
            "chrome_path": r"C:\Chrome\chrome.exe",
            "chromedriver_path": r"C:\Driver\chromedriver.exe",
            "bundled_drivers_dir": r"C:\App\drivers",
            "cache_drivers_dir": r"C:\Data\GoogleFormTool\drivers",
            "mode": "electron",
        },
    )

    response = client.get("/settings/diagnostics")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Runtime Diagnostics" in text
    assert "C:\\Data\\GoogleFormTool" in text
    assert "C:\\Chrome\\chrome.exe" in text
    assert "C:\\Driver\\chromedriver.exe" in text
    assert "Bundled Chromium is not included" in text
