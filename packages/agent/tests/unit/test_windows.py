import pytest

from sanvik_agent.execution import windows


def test_chrome_is_found_on_system_path(monkeypatch) -> None:
    chrome_path = r"C:\Installed\Chrome\chrome.exe"
    monkeypatch.setattr(windows.shutil, "which", lambda name: chrome_path)

    result = windows.find_chrome()

    assert result == chrome_path


def test_chrome_opens_default_profile(monkeypatch) -> None:
    calls = []
    chrome_window = object()

    monkeypatch.setattr(
        windows,
        "find_chrome",
        lambda: r"C:\Installed\Chrome\chrome.exe",
    )
    monkeypatch.setattr(
        windows.subprocess,
        "Popen",
        lambda arguments: calls.append(("launch", arguments)),
    )
    monkeypatch.setattr(
        windows,
        "wait_for_application_window",
        lambda application: calls.append(("wait", application)) or chrome_window,
    )

    result = windows.open_application("chrome.exe")

    assert result is chrome_window
    assert calls == [
        (
            "launch",
            [
                r"C:\Installed\Chrome\chrome.exe",
                "--profile-directory=Default",
                "--new-window",
            ],
        ),
        ("wait", "chrome"),
    ]


def test_file_explorer_open_uses_desktop_window_lookup(monkeypatch) -> None:
    calls = []
    explorer_window = object()

    monkeypatch.setattr(
        windows.subprocess,
        "Popen",
        lambda arguments: calls.append(("launch", arguments)),
    )
    monkeypatch.setattr(
        windows,
        "wait_for_application_window",
        lambda application: calls.append(("wait", application)) or explorer_window,
    )

    result = windows.open_application("explorer.exe")

    assert result is explorer_window
    assert calls == [
        ("launch", ["explorer.exe"]),
        ("wait", "file_explorer"),
    ]


@pytest.mark.parametrize(
    "application,window_class,expected_process",
    [
        ("chrome", "Chrome_WidgetWin_1", "chrome.exe"),
        ("file_explorer", "CabinetWClass", "explorer.exe"),
    ],
)
def test_application_windows_are_filtered_by_owning_process(
    monkeypatch,
    application,
    window_class,
    expected_process,
) -> None:
    import pywinauto

    calls = []
    wrong_window = FakeFoundWindow(handle=10, process_id=100)
    correct_window = FakeFoundWindow(handle=20, process_id=200)
    selected_window = object()

    monkeypatch.setattr(
        pywinauto,
        "Desktop",
        lambda backend: FakeWindowListDesktop(
            backend,
            [wrong_window, correct_window],
            {20: selected_window},
            calls,
        ),
    )
    monkeypatch.setattr(
        windows,
        "get_process_name",
        lambda process_id: {
            100: "code.exe",
            200: expected_process,
        }[process_id],
    )

    result = windows.find_application_windows(application)

    assert result == [selected_window]
    assert calls == [
        ("desktop_backend", "uia"),
        ("windows", window_class, True),
        ("window", 20),
    ]


def test_window_is_closed_and_verified() -> None:
    calls = []
    window = FakeWindow(calls)

    windows.close_application(window)
    windows.verify_application_closed(window)

    assert calls == [
        ("close",),
        ("wait_not", "exists", 10),
    ]


class FakeWindowListDesktop:
    def __init__(self, backend, visible_windows, selected_windows, calls) -> None:
        calls.append(("desktop_backend", backend))
        self.visible_windows = visible_windows
        self.selected_windows = selected_windows
        self.calls = calls

    def windows(self, class_name, visible_only):
        self.calls.append(("windows", class_name, visible_only))
        return self.visible_windows

    def window(self, handle):
        self.calls.append(("window", handle))
        return self.selected_windows[handle]


class FakeFoundWindow:
    def __init__(self, handle, process_id) -> None:
        self.handle = handle
        self._process_id = process_id

    def process_id(self):
        return self._process_id


class FakeWindow:
    def __init__(self, calls) -> None:
        self.calls = calls

    def close(self):
        self.calls.append(("close",))

    def wait_not(self, state, timeout):
        self.calls.append(("wait_not", state, timeout))
