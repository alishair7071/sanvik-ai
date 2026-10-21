"""Simple YouTube video workflow built on Sanvik's browser layer."""

from sanvik_agent.execution.browser import BrowserSession, verify_page_domain


YOUTUBE_URL = "https://www.youtube.com"
SEARCH_BOX_SELECTOR = 'input[name="search_query"]'
VIDEO_RESULT_SELECTOR = "ytd-video-renderer"
FIRST_VIDEO_LINK_SELECTOR = "ytd-video-renderer a#thumbnail"
VIDEO_PLAYER_SELECTOR = "video"
RESULTS_TIMEOUT = 20_000


# Check that a user-provided search query is safe and useful before using it.
def validate_search_query(query: str) -> str:
    if not isinstance(query, str):
        raise ValueError("YouTube search query must be text")

    query = query.strip()

    if not query:
        raise ValueError("YouTube search query must not be empty")

    if len(query) > 200:
        raise ValueError("YouTube search query is too long")

    return query


# Accept YouTube's English cookie consent button when it appears on a new profile.
def accept_youtube_consent(page) -> None:
    consent_button = page.get_by_role("button", name="Accept all")

    if consent_button.count() > 0:
        consent_button.first.click()
        page.wait_for_timeout(500)


# Open YouTube, submit one search query, and confirm that video results appeared.
def search_youtube(session: BrowserSession, query: str) -> dict:
    query = validate_search_query(query)

    page = session.open_page(YOUTUBE_URL)
    verify_page_domain(page, "youtube.com")
    accept_youtube_consent(page)

    search_box = page.locator(SEARCH_BOX_SELECTOR).first
    search_box.wait_for(state="visible", timeout=10_000)
    search_box.fill(query)
    search_box.press("Enter")

    page.wait_for_url(
        "**/results?search_query=*",
        wait_until="domcontentloaded",
        timeout=10_000,
    )
    verify_page_domain(page, "youtube.com")

    video_results = page.locator(VIDEO_RESULT_SELECTOR)
    video_results.first.wait_for(state="visible", timeout=RESULTS_TIMEOUT)
    result_count = video_results.count()

    if result_count == 0:
        raise RuntimeError("YouTube search results did not appear")

    return {
        "query": query,
        "url": page.url,
        "result_count": result_count,
    }


# Open the first normal video result from the current YouTube search page.
def open_first_video_result(page) -> None:
    video_link = page.locator(FIRST_VIDEO_LINK_SELECTOR).first
    video_link.wait_for(state="visible", timeout=10_000)
    video_link.click()

    page.wait_for_url(
        "**/watch?*",
        wait_until="domcontentloaded",
        timeout=10_000,
    )
    verify_page_domain(page, "youtube.com")


# Confirm that the YouTube player starts and its playback time becomes positive.
def verify_video_playing(page) -> dict:
    video_player = page.locator(VIDEO_PLAYER_SELECTOR).first
    video_player.wait_for(state="visible", timeout=10_000)

    if video_player.evaluate("video => video.paused"):
        video_player.click()

    try:
        page.wait_for_function(
            """() => {
                const video = document.querySelector("video")
                return video && !video.paused && video.currentTime > 0
            }""",
            timeout=10_000,
        )
    except Exception as error:
        raise RuntimeError("YouTube video playback could not be verified") from error

    return {
        "playing": True,
        "current_time": video_player.evaluate("video => video.currentTime"),
    }


# Search for a video, open the first result, and verify that it is playing.
def play_youtube_video(session: BrowserSession, query: str) -> dict:
    search_result = search_youtube(session, query)
    page = session.page

    open_first_video_result(page)
    playback = verify_video_playing(page)

    return {
        "success": True,
        "query": search_result["query"],
        "title": page.title(),
        "url": page.url,
        "playing": playback["playing"],
    }