# Google Form Automation Tool

## Tests

Run the default unit test suite without Selenium integration tests:

```powershell
.\venv\Scripts\python.exe -m pytest
```

Run real Selenium/Google Forms integration tests explicitly:

```powershell
.\venv\Scripts\python.exe -m pytest -m integration
```

Integration tests require a working Chrome and ChromeDriver setup.
