from sanvik_agent.execution import windows


def test_chrome_is_found_on_system_path(monkeypatch) -> None:
    chrome_path = r"C:\Installed\Chrome\chrome.exe"
    monkeypatch.setattr(windows.shutil, "which", lambda name: chrome_path)

    result = windows.find_chrome()

    assert result == chrome_path


def test_chrome_opens_default_profile(monkeypatch) -> None:
    import pywinauto

    calls = []
    chrome_window = FakeWindow(calls)

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
        pywinauto,
        "Desktop",
        lambda backend: FakeDesktop(backend, chrome_window, calls),
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
        ("desktop_backend", "uia"),
        ("desktop_window", "Chrome_WidgetWin_1", 0),
        ("wait", "visible", 10),
    ]


class FakeDesktop:
    def __init__(self, backend, window, calls) -> None:
        calls.append(("desktop_backend", backend))
        self.result = window
        self.calls = calls

    def window(self, class_name, found_index):
        self.calls.append(("desktop_window", class_name, found_index))
        return self.result


class FakeWindow:
    def __init__(self, calls) -> None:
        self.calls = calls

    def wait(self, state, timeout):
        self.calls.append(("wait", state, timeout))
