"""Small Windows UI Automation layer for supported applications."""

import os
import shutil
from pathlib import Path



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



# Open the validated executable and return its visible window.
def open_application(executable: str):
    from pywinauto.application import Application

    if executable == "chrome.exe":
        executable = find_chrome()

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
    if not window.is_visible():
        raise RuntimeError("Application window is not visible")



# Read the Edit control and compare it with the requested text.
def verify_text(window, expected_text: str) -> None:
    editor = window.child_window(control_type="Edit")
    if editor.get_value() != expected_text:
        raise RuntimeError("Application text could not be verified")
