# Google Form Automation Tool

Local web tool for extracting Google Form structure, preparing answer data, and running automated submissions from your own machine.

## Quick Start on Windows

1. Install Python 3.9 or newer.
2. Open PowerShell in this project folder.
3. Create a virtual environment:

```powershell
py -3 -m venv venv
```

4. Install dependencies:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

5. Create your local environment file:

```powershell
Copy-Item .env.example .env
```

6. Edit `.env` and set:

```env
SECRET_KEY=change-this-to-a-random-string
DB_PATH=app/services/db.json
CHROME_BINARY_PATH=D:\common_tool\google_form_automation_tool\drivers\chrome\chrome.exe
CHROME_DRIVER_PATH=D:\common_tool\google_form_automation_tool\drivers\chromedriver\chromedriver.exe
```

7. Start the app:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1
```

8. Open:

```text
http://localhost:5000
```

## Chrome and ChromeDriver

Selenium features require a working Chrome or Chromium binary and a compatible ChromeDriver.

Suggested Windows folder layout:

```text
D:\common_tool\google_form_automation_tool\drivers\chrome\chrome.exe
D:\common_tool\google_form_automation_tool\drivers\chromedriver\chromedriver.exe
```

You can use another folder if you update `CHROME_BINARY_PATH` and `CHROME_DRIVER_PATH` in `.env`.

Chrome and ChromeDriver versions must be compatible. If extraction or submission fails before opening the form, check these paths and versions first.

## Local Run Script

Use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1
```

The script:

- runs from the repo root,
- uses `.\venv\Scripts\python.exe`,
- prints setup instructions if the virtual environment is missing,
- warns if `.env` is missing,
- starts `wsgi.py`,
- shows `http://localhost:5000`.

It does not install dependencies automatically.

## Docker Optional

Docker is an advanced path for users who prefer containerized setup.

The repo includes `Dockerfile` and `docker-compose.yml`. A Docker image can use Chromium inside the container, which avoids configuring local Windows Chrome paths. Treat Docker as optional until the browser setup in the image is verified for your machine.

Typical command:

```powershell
docker compose up --build
```

Then open `http://localhost:5000`.

## Future EXE Packaging

EXE packaging is not implemented in this TIP.

A future packaging pass can use PyInstaller or a similar tool. Browser packaging needs explicit testing because Chrome/Chromium and ChromeDriver paths are the riskiest part of a standalone desktop build.

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

### Test Google Form URL

To point integration tests at your own real Google Form (recommended for beta verification), add this to `.env`:

```env
TEST_GOOGLE_FORM_URL=https://docs.google.com/forms/d/e/<your-form-id>/viewform
```

When set, the `sample_form_url` fixture in `tests/conftest.py` uses it. If unset, tests fall back to the bundled sample form URL. Unit tests do not require this variable.
