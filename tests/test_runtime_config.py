import importlib
from pathlib import Path


def test_app_data_path_uses_appdata(monkeypatch):
    monkeypatch.setenv("APPDATA", r"C:\Users\Example\AppData\Roaming")
    monkeypatch.setenv("DB_PATH", "")
    monkeypatch.setenv("LOG_DIR", "")
    monkeypatch.setenv("DRIVERS_DIR", "")

    import config

    reloaded = importlib.reload(config)

    assert reloaded.get_app_data_path() == Path(r"C:\Users\Example\AppData\Roaming") / "GoogleFormTool"
    assert reloaded.Config.APP_DATA_PATH == str(Path(r"C:\Users\Example\AppData\Roaming") / "GoogleFormTool")
    assert reloaded.Config.DB_PATH == str(Path(reloaded.Config.APP_DATA_PATH) / "db.json")
    assert reloaded.Config.LOG_DIR == str(Path(reloaded.Config.APP_DATA_PATH) / "logs")
    assert reloaded.Config.DRIVERS_DIR == str(Path(reloaded.Config.APP_DATA_PATH) / "drivers")


def test_app_data_path_falls_back_to_home(monkeypatch, tmp_path):
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("DB_PATH", "")
    monkeypatch.setenv("LOG_DIR", "")
    monkeypatch.setenv("DRIVERS_DIR", "")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    import config

    reloaded = importlib.reload(config)

    assert reloaded.get_app_data_path() == tmp_path / "GoogleFormTool"
    assert reloaded.Config.APP_DATA_PATH == str(tmp_path / "GoogleFormTool")
