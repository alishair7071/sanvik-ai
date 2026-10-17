from sanvik_agent.execution import windows


def test_chrome_is_found_on_system_path(monkeypatch) -> None:
    chrome_path = r"C:InstalledChromechrome.exe"
    monkeypatch.setattr(windows.shutil, "which", lambda name: chrome_path)

    result = windows.find_chrome()

    assert result == chrome_path
