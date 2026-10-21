"""Small Playwright browser layer for future web automation tasks."""

import os
from pathlib import Path
from urllib.parse import urlparse



# Keep Sanvik's cookies and Google login separate from the user's normal Chrome profile.
def default_profile_directory() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")

    if local_app_data:
        base_directory = Path(local_app_data)
    else:
        base_directory = Path.home() / "AppData" / "Local"

    return base_directory / "Sanvik AI" / "browser-profile"


# Manage one visible Playwright-controlled Chrome browser and its persistent profile.
class BrowserSession:
    def __init__(self, profile_directory: Path | None = None, playwright_factory=None):
        if profile_directory is None:
            profile_directory = default_profile_directory()

        self.profile_directory = profile_directory
        self.playwright_factory = playwright_factory
        self.playwright = None
        self.context = None
        self.page = None


    # Start Chrome only once and keep the browser open until close() is called.
    def start(self):
        if self.page is not None:
            return self.page

        self.profile_directory.mkdir(parents=True, exist_ok=True)

        if self.playwright_factory is None:
            from playwright.sync_api import sync_playwright

            playwright_manager = sync_playwright()
        else:
            playwright_manager = self.playwright_factory()

        self.playwright = playwright_manager.start()
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_directory),
            channel="chrome",
            headless=False,
        )

        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()

        return self.page


    # Open a normal web address in Sanvik's managed browser.
    def open_page(self, url: str):
        parsed_url = urlparse(url)

        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("Browser URL must be a complete http or https address")

        page = self.start()
        page.goto(url, wait_until="domcontentloaded")
        return page


    # Close the browser and release Playwright resources during application shutdown.
    def close(self) -> None:
        if self.context is not None:
            self.context.close()
            self.context = None

        if self.playwright is not None:
            self.playwright.stop()
            self.playwright = None

        self.page = None


# Confirm that the browser reached the expected website domain.
def verify_page_domain(page, expected_domain: str) -> dict:
    expected_domain = expected_domain.strip().lower()

    if not expected_domain:
        raise ValueError("Expected website domain must not be empty")

    hostname = urlparse(page.url).hostname

    if hostname is None:
        raise RuntimeError(f"{expected_domain} did not load")

    if hostname != expected_domain and not hostname.endswith(f".{expected_domain}"):
        raise RuntimeError(f"{expected_domain} did not load")

    return {
        "url": page.url,
        "title": page.title(),
    }