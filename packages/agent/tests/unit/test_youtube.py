import pytest

from sanvik_agent.execution.youtube import (
    play_youtube_video,
    search_youtube,
    validate_search_query,
)


class FakeLocator:
    def __init__(self, page, selector, count=1):
        self.page = page
        self.selector = selector
        self.result_count = count
        self.wait_calls = []
        self.filled_text = None
        self.pressed_key = None
        self.clicked = False


    @property
    def first(self):
        return self


    def wait_for(self, state, timeout):
        self.wait_calls.append((state, timeout))


    def fill(self, text):
        self.filled_text = text


    def press(self, key):
        self.pressed_key = key
        self.page.url = "https://www.youtube.com/results?search_query=test"


    def click(self):
        self.clicked = True

        if self.selector == "video":
            self.page.video_is_paused = False
        elif self.selector == "consent":
            self.page.consent_accepted = True
        else:
            self.page.url = "https://www.youtube.com/watch?v=test-video"


    def count(self):
        return self.result_count


    def evaluate(self, expression):
        if expression == "video => video.paused":
            return self.page.video_is_paused

        if expression == "video => video.currentTime":
            return self.page.current_time

        raise AssertionError(f"Unexpected browser expression: {expression}")


class FakePage:
    def __init__(self, result_count=1, playback_works=True, video_is_paused=False, consent_visible=False):
        self.url = "https://www.youtube.com"
        self.search_box = FakeLocator(self, 'input[name="search_query"]')
        self.video_results = FakeLocator(self, "ytd-video-renderer", result_count)
        self.first_video_link = FakeLocator(self, "ytd-video-renderer a#thumbnail")
        self.video_player = FakeLocator(self, "video")
        self.consent_button = FakeLocator(self, "consent", int(consent_visible))
        self.consent_accepted = False
        self.waited_urls = []
        self.waited_times = []
        self.waited_functions = []
        self.video_is_paused = video_is_paused
        self.playback_works = playback_works
        self.current_time = 0.0


    def locator(self, selector):
        if selector == 'input[name="search_query"]':
            return self.search_box

        if selector == "ytd-video-renderer":
            return self.video_results

        if selector == "ytd-video-renderer a#thumbnail":
            return self.first_video_link

        if selector == "video":
            return self.video_player

        raise AssertionError(f"Unexpected selector: {selector}")


    def get_by_role(self, role, name):
        if role == "button" and name == "Accept all":
            return self.consent_button

        raise AssertionError(f"Unexpected role: {role} {name}")


    def wait_for_url(self, pattern, wait_until, timeout):
        self.waited_urls.append((pattern, wait_until, timeout))


    def wait_for_timeout(self, timeout):
        self.waited_times.append(timeout)


    def wait_for_function(self, function, timeout):
        self.waited_functions.append((function, timeout))

        if not self.playback_works:
            raise TimeoutError("Playback did not start")

        self.current_time = 1.0


    def title(self):
        return "Example Video - YouTube"


class FakeSession:
    def __init__(self, page):
        self.page = page
        self.opened_urls = []


    def open_page(self, url):
        self.opened_urls.append(url)
        return self.page


def test_search_youtube_fills_the_search_box_and_returns_results() -> None:
    page = FakePage(result_count=3)
    session = FakeSession(page)

    result = search_youtube(session, "  lofi hip hop  ")

    assert result == {
        "query": "lofi hip hop",
        "url": "https://www.youtube.com/results?search_query=test",
        "result_count": 3,
    }
    assert session.opened_urls == ["https://www.youtube.com"]
    assert page.search_box.filled_text == "lofi hip hop"
    assert page.search_box.pressed_key == "Enter"
    assert page.waited_urls == [
        ("**/results?search_query=*", "domcontentloaded", 10_000),
    ]


def test_search_youtube_accepts_consent_when_it_is_visible() -> None:
    page = FakePage(consent_visible=True)
    session = FakeSession(page)

    search_youtube(session, "Big Buck Bunny")

    assert page.consent_button.clicked is True
    assert page.consent_accepted is True
    assert page.waited_times == [500]


def test_play_youtube_video_opens_the_first_result_and_verifies_playback() -> None:
    page = FakePage()
    session = FakeSession(page)

    result = play_youtube_video(session, "Big Buck Bunny")

    assert result == {
        "success": True,
        "query": "Big Buck Bunny",
        "title": "Example Video - YouTube",
        "url": "https://www.youtube.com/watch?v=test-video",
        "playing": True,
    }
    assert page.first_video_link.clicked is True
    assert page.waited_urls == [
        ("**/results?search_query=*", "domcontentloaded", 10_000),
        ("**/watch?*", "domcontentloaded", 10_000),
    ]
    assert page.waited_functions[0][1] == 25_000


def test_play_video_clicks_the_player_when_it_starts_paused() -> None:
    page = FakePage(video_is_paused=True)
    session = FakeSession(page)

    result = play_youtube_video(session, "test video")

    assert result["playing"] is True
    assert page.video_player.clicked is True


@pytest.mark.parametrize("query", ["", "   ", "x" * 201])
def test_invalid_search_text_is_rejected_before_the_browser_opens(query) -> None:
    page = FakePage()
    session = FakeSession(page)

    with pytest.raises(ValueError):
        search_youtube(session, query)

    assert session.opened_urls == []


def test_non_text_search_query_is_rejected() -> None:
    with pytest.raises(ValueError, match="must be text"):
        validate_search_query(42)


def test_search_fails_when_no_video_results_are_found() -> None:
    page = FakePage(result_count=0)
    session = FakeSession(page)

    with pytest.raises(RuntimeError, match="results did not appear"):
        search_youtube(session, "test video")


def test_play_video_fails_when_playback_does_not_advance() -> None:
    page = FakePage(playback_works=False)
    session = FakeSession(page)

    with pytest.raises(RuntimeError, match="playback could not be verified"):
        play_youtube_video(session, "test video")