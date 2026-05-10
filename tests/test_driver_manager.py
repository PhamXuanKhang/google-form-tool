from pathlib import Path

import app.core.driver_manager as driver_manager


def test_chrome_and_driver_explicit_overrides_win(monkeypatch):
    driver_manager._cache.clear()

    assert driver_manager.get_chrome_binary(r"C:\Chrome\chrome.exe") == r"C:\Chrome\chrome.exe"
    assert driver_manager.get_chromedriver_path(r"C:\Driver\chromedriver.exe") == r"C:\Driver\chromedriver.exe"


def test_chrome_binary_uses_bundled_lookup_before_system_install(monkeypatch, tmp_path):
    driver_manager._cache.clear()
    app_root = tmp_path / "app-drivers"
    system_root = tmp_path / "system"
    bundled = app_root / "chrome" / "chrome.exe"
    system = system_root / "Google" / "Chrome" / "Application" / "chrome.exe"
    bundled.parent.mkdir(parents=True)
    system.parent.mkdir(parents=True)
    bundled.write_text("bundled", encoding="utf-8")
    system.write_text("system", encoding="utf-8")

    monkeypatch.setattr(driver_manager, "_app_drivers_root", lambda: app_root)
    monkeypatch.setattr(driver_manager, "_win_chrome_candidates", lambda: [system])

    assert driver_manager.get_chrome_binary() == str(bundled)


def test_chrome_binary_uses_system_install_after_bundled_lookup(monkeypatch, tmp_path):
    driver_manager._cache.clear()
    app_root = tmp_path / "app-drivers"
    system = tmp_path / "system" / "Google" / "Chrome" / "Application" / "chrome.exe"
    system.parent.mkdir(parents=True)
    system.write_text("system", encoding="utf-8")

    monkeypatch.setattr(driver_manager, "_app_drivers_root", lambda: app_root)
    monkeypatch.setattr(driver_manager, "_win_chrome_candidates", lambda: [system])

    assert driver_manager.get_chrome_binary() == str(system)


def test_chromedriver_uses_bundled_lookup_before_cache(monkeypatch, tmp_path):
    driver_manager._cache.clear()
    app_root = tmp_path / "app-drivers"
    cache_root = tmp_path / "cache-drivers"
    bundled = app_root / "chromedriver" / "chromedriver.exe"
    cached = cache_root / "chromedriver" / "chromedriver.exe"
    bundled.parent.mkdir(parents=True)
    cached.parent.mkdir(parents=True)
    bundled.write_text("bundled", encoding="utf-8")
    cached.write_text("cached", encoding="utf-8")

    monkeypatch.setattr(driver_manager, "_app_drivers_root", lambda: app_root)
    monkeypatch.setattr(driver_manager, "_cache_drivers_root", lambda: cache_root)

    assert driver_manager.get_chromedriver_path() == str(bundled)


def test_chromedriver_no_download_mode_returns_none_without_import(monkeypatch, tmp_path):
    driver_manager._cache.clear()
    app_root = tmp_path / "app-drivers"
    cache_root = tmp_path / "app-data" / "drivers"

    monkeypatch.setattr(driver_manager, "_app_drivers_root", lambda: app_root)
    monkeypatch.setattr(driver_manager, "_cache_drivers_root", lambda: cache_root)

    assert driver_manager.get_chromedriver_path(allow_download=False) is None
    assert not cache_root.exists()


def test_chromedriver_download_cache_target_is_app_data(monkeypatch, tmp_path):
    driver_manager._cache.clear()
    app_root = tmp_path / "app-drivers"
    cache_root = tmp_path / "app-data" / "drivers"
    downloaded = tmp_path / "downloaded.exe"
    downloaded.write_text("downloaded", encoding="utf-8")

    class FakeChromeDriverManager:
        def __init__(self, cache_manager=None):
            self.cache_manager = cache_manager

        def install(self):
            return str(downloaded)

    class FakeDriverCacheManager:
        def __init__(self, root_dir=None):
            self.root_dir = root_dir

    monkeypatch.setattr(driver_manager, "_app_drivers_root", lambda: app_root)
    monkeypatch.setattr(driver_manager, "_cache_drivers_root", lambda: cache_root)
    monkeypatch.setattr(driver_manager.shutil, "copy2", lambda source, target: Path(target).write_text(Path(source).read_text(encoding="utf-8"), encoding="utf-8"))
    monkeypatch.setitem(__import__("sys").modules, "webdriver_manager.chrome", type("Module", (), {"ChromeDriverManager": FakeChromeDriverManager}))
    monkeypatch.setitem(__import__("sys").modules, "webdriver_manager.core.driver_cache", type("Module", (), {"DriverCacheManager": FakeDriverCacheManager}))

    result = driver_manager.get_chromedriver_path()

    assert result == str(cache_root / "chromedriver" / "chromedriver.exe")
    assert Path(result).read_text(encoding="utf-8") == "downloaded"
