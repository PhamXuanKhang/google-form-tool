"""Every page must render with assets served by the app itself.

The desktop app has to work without network access, so scripts, stylesheets,
icons, images, and fonts may not point at a CDN. Outbound navigation links
(GitHub, LinkedIn, mailto) are not assets and are allowed.
"""
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

import app.routes.pages as pages_routes


VENDOR_DIR = Path(__file__).resolve().parents[1] / "app" / "static" / "vendor"

PAGES = ["/", "/form_filling", "/form_copy", "/settings/diagnostics", "/about"]

TAG_PATTERNS = [
    re.compile(r"<script\b[^>]*\bsrc=[\"']([^\"']+)[\"']", re.IGNORECASE),
    re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", re.IGNORECASE),
    re.compile(r"<link\b[^>]*\bhref=[\"']([^\"']+)[\"']", re.IGNORECASE),
]
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
CSS_URL = re.compile(r"(?:url\(\s*[\"']?|@import\s+[\"'])([^\"')]+)", re.IGNORECASE)
INLINE_CSS = re.compile(r"<style\b[^>]*>(.*?)</style>|\bstyle=\"([^\"]*)\"", re.IGNORECASE | re.DOTALL)


class EmptyStorage:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def get_all_forms_summary(self):
        return []


@pytest.fixture
def offline_client(client, storage_stub, monkeypatch):
    storage_stub(EmptyStorage())
    monkeypatch.setattr(
        pages_routes,
        "_runtime_diagnostics",
        lambda: {
            "app_data_path": "C:/Data",
            "db_path": "C:/Data/db.json",
            "log_path": "C:/Data/logs",
            "chrome_path": None,
            "chromedriver_path": None,
            "bundled_drivers_dir": "C:/App/drivers",
            "cache_drivers_dir": "C:/Data/drivers",
            "mode": "dev",
        },
    )
    return client


def _asset_urls(html):
    html = HTML_COMMENT.sub("", html)
    urls = []
    for pattern in TAG_PATTERNS:
        urls.extend(match.group(1).strip() for match in pattern.finditer(html))
    for block in INLINE_CSS.finditer(html):
        css = block.group(1) or block.group(2) or ""
        urls.extend(match.group(1).strip() for match in CSS_URL.finditer(css))
    return [url for url in urls if not url.startswith(("data:", "#"))]


def _is_external(url):
    return url.startswith("//") or urlparse(url).scheme in {"http", "https"}


@pytest.mark.parametrize("lang", ["en", "vi"])
@pytest.mark.parametrize("path", PAGES)
def test_page_assets_are_served_locally(offline_client, path, lang):
    response = offline_client.get(f"{path}?lang={lang}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    urls = _asset_urls(html)
    assert urls, f"no assets found on {path}"
    external = [url for url in urls if _is_external(url)]
    assert external == [], f"{path} loads external assets: {external}"

    for url in urls:
        asset = offline_client.get(urlparse(url).path)
        assert asset.status_code == 200, f"{path} references missing asset {url}"
        asset.close()


def test_vendor_stylesheets_reference_only_bundled_files():
    stylesheets = list(VENDOR_DIR.rglob("*.css"))
    assert stylesheets

    for stylesheet in stylesheets:
        css = stylesheet.read_text(encoding="utf-8")
        for match in CSS_URL.finditer(css):
            url = match.group(1).strip()
            if url.startswith("data:"):
                continue
            assert not _is_external(url), f"{stylesheet.name} loads {url}"
            target = (stylesheet.parent / urlparse(url).path).resolve()
            assert target.is_file(), f"{stylesheet.name} references missing {url}"


def test_each_vendor_library_ships_its_license():
    libraries = [entry for entry in VENDOR_DIR.iterdir() if entry.is_dir()]
    assert libraries

    for library in libraries:
        licenses = [p for p in library.iterdir() if p.name.lower().startswith("license")]
        assert licenses, f"{library.name} has no LICENSE file"
