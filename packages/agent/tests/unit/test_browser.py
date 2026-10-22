import pytest

from sanvik_agent.execution import browser
from sanvik_agent.execution.browser import BrowserSession, verify_page_domain


class FakePage:
    def __init__(self):
        self.url = "about:blank"
        self.visited_urls = []


    def goto(self, url, wait_until):
        self.visited_urls.append((url, wait_until))
        self.url = url


    def title(self):
        return "Example page"


class FakeContext:
    def __init__(self, page):
        self.pages = [page]
        self.closed = False


    def close(self):
        self.closed = True


class FakeChromium:
    def __init__(self, context):
        self.context = context
        self.launch_arguments = None


    def launch_persistent_context(self, **arguments):
        self.launch_arguments = arguments
        return self.context


class FakePlaywright:
    def __init__(self, chromium):
        self.chromium = chromium
        self.stopped = False


    def stop(self):
        self.stopped = True


class FakePlaywrightManager:
    def __init__(self, playwright):
        self.playwright = playwright


    def start(self):
        return self.playwright


def make_session(tmp_path):
    page = FakePage()
    context = FakeContext(page)
    chromium = FakeChromium(context)
    playwright = FakePlaywright(chromium)
    manager = FakePlaywrightManager(playwright)
    session = BrowserSession(
        profile_directory=tmp_path / "browser-profile",
        playwright_factory=lambda: manager,
    )
    return session, page, context, chromium, playwright


def test_open_page_uses_a_persistent_chrome_profile(tmp_path) -> None:
    session, page, _, chromium, _ = make_session(tmp_path)

    opened_page = session.open_page("https://www.youtube.com")
    result = verify_page_domain(opened_page, "youtube.com")

    assert result == {
        "url": "https://www.youtube.com",
        "title": "Example page",
    }
    assert page.visited_urls == [
        ("https://www.youtube.com", "domcontentloaded"),
    ]
    assert chromium.launch_arguments == {
        "user_data_dir": str(tmp_path / "browser-profile"),
        "channel": "chrome",
        "headless": False,
    }


def test_open_page_rejects_incomplete_or_unsafe_urls(tmp_path) -> None:
    session, _, _, _, _ = make_session(tmp_path)

    with pytest.raises(ValueError, match="http or https"):
        session.open_page("file:///C:/private-file.txt")

    with pytest.raises(ValueError, match="http or https"):
        session.open_page("youtube.com")


def test_verify_page_domain_rejects_an_unexpected_page(tmp_path) -> None:
    session, page, _, _, _ = make_session(tmp_path)

    def visit_unexpected_page(url, wait_until):
        page.url = "https://notyoutube.com"

    page.goto = visit_unexpected_page
    opened_page = session.open_page("https://www.youtube.com")

    with pytest.raises(RuntimeError, match="youtube.com did not load"):
        verify_page_domain(opened_page, "youtube.com")


def test_verify_page_domain_accepts_subdomains() -> None:
    page = FakePage()
    page.url = "https://docs.github.com"

    result = verify_page_domain(page, "github.com")

    assert result["url"] == "https://docs.github.com"


def test_close_releases_browser_resources(tmp_path) -> None:
    session, _, context, _, playwright = make_session(tmp_path)
    session.start()

    session.close()

    assert context.closed is True
    assert playwright.stopped is True
    assert session.page is None

def test_managed_browser_session_is_shared_and_can_be_closed(monkeypatch) -> None:
    class FakeManagedSession:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    session = FakeManagedSession()
    monkeypatch.setattr(browser, "_managed_browser_session", None)
    monkeypatch.setattr(browser, "BrowserSession", lambda: session)

    first_session = browser.get_managed_browser_session()
    second_session = browser.get_managed_browser_session()

    assert first_session is session
    assert second_session is session

    browser.close_managed_browser_session()

    assert session.closed is True
    assert browser._managed_browser_session is None