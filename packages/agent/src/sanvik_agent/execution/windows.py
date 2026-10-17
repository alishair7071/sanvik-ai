"""Small Windows UI Automation layer for supported applications."""

import os
import shutil
import subprocess
from pathlib import Path

DEFAULT_CHROME_PROFILE = "Default"



# Find Chrome without asking the LLM for a machine-specific file path.
def find_chrome() -> str:
    chrome_on_path = shutil.which("chrome.exe")
    if chrome_on_path:
        return chrome_on_path

    folders = [
        os.environ.get("PROGRAMFILES"),
        os.environ.get("PROGRAMFILES(X86)"),
        os.environ.get("LOCALAPPDATA"),
    ]

    for folder in folders:
        if folder:
            chrome_path = Path(folder) / "Google" / "Chrome" / "Application" / "chrome.exe"
            if chrome_path.is_file():
                return str(chrome_path)

    raise RuntimeError("Google Chrome is not installed")



# Open Chrome directly in the trusted default profile.
def open_chrome():
    from pywinauto import Desktop

    chrome_path = find_chrome()
    arguments = [
        chrome_path,
        f"--profile-directory={DEFAULT_CHROME_PROFILE}",
        "--new-window",
    ]
    subprocess.Popen(arguments)

    # Chrome may create its window in a different process from the one started
    # above, so find the visible browser window from the desktop.
    window = Desktop(backend="uia").window(
        class_name="Chrome_WidgetWin_1",
        found_index=0,
    )
    window.wait("visible", timeout=10)
    return window



# Open the validated executable and return its visible window.
def open_application(executable: str):
    if executable == "chrome.exe":
        return open_chrome()

    from pywinauto.application import Application

    app = Application(backend="uia").start(executable)
    window = app.top_window()
    window.wait("visible", timeout=10)
    return window



# Put text into the application's accessible Edit control.
def type_text(window, text: str) -> None:
    editor = window.child_window(control_type="Edit")
    editor.wait("visible", timeout=5)
    editor.set_edit_text(text)



# Confirm that the application window is visible.
def verify_application(window) -> None:
    window.wait("visible", timeout=5)



# Read the Edit control and compare it with the requested text.
def verify_text(window, expected_text: str) -> None:
    editor = window.child_window(control_type="Edit")
    if editor.get_value() != expected_text:
        raise RuntimeError("Application text could not be verified")
