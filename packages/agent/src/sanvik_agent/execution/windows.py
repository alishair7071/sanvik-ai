"""Small Windows UI Automation layer for supported applications."""

import os
import shutil
import subprocess
import time
from pathlib import Path

DEFAULT_CHROME_PROFILE = "Default"

APPLICATION_WINDOW_CLASSES = {
    "chrome": "Chrome_WidgetWin_1",
    "file_explorer": "CabinetWClass",
}

APPLICATION_PROCESS_NAMES = {
    "chrome": "chrome.exe",
    "file_explorer": "explorer.exe",
}



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



# Return the executable name that owns a window.
def get_process_name(process_id: int) -> str:
    from pywinauto.application import process_module

    process_path = process_module(process_id)
    return Path(process_path).name.lower()



# Find visible windows belonging to an approved application.
def find_application_windows(application_name: str) -> list:
    from pywinauto import Desktop

    window_class = APPLICATION_WINDOW_CLASSES.get(application_name)
    process_name = APPLICATION_PROCESS_NAMES.get(application_name)

    if window_class is None or process_name is None:
        raise RuntimeError("Application window lookup is not supported")

    desktop = Desktop(backend="uia")
    found_windows = desktop.windows(
        class_name=window_class,
        visible_only=True,
    )

    windows = []

    for found_window in found_windows:
        try:
            owner = get_process_name(found_window.process_id())
        except Exception:
            continue

        if owner == process_name:
            windows.append(desktop.window(handle=found_window.handle))

    return windows



# Wait until at least one real application window is visible.
def wait_for_application_window(application_name: str):
    deadline = time.monotonic() + 10

    while time.monotonic() < deadline:
        windows = find_application_windows(application_name)

        if windows:
            window = windows[0]
            window.wait("visible", timeout=1)
            return window

        time.sleep(0.2)

    raise RuntimeError("Application window did not become visible")



# Open Chrome directly in the trusted default profile.
def open_chrome():
    chrome_path = find_chrome()
    arguments = [
        chrome_path,
        f"--profile-directory={DEFAULT_CHROME_PROFILE}",
        "--new-window",
    ]
    subprocess.Popen(arguments)
    return wait_for_application_window("chrome")



# Open the validated executable and return its visible window.
def open_application(executable: str):
    if executable == "chrome.exe":
        return open_chrome()

    if executable == "explorer.exe":
        subprocess.Popen([executable])
        return wait_for_application_window("file_explorer")

    from pywinauto.application import Application

    app = Application(backend="uia").start(executable)
    window = app.top_window()
    window.wait("visible", timeout=10)
    return window



# Ask an application window to close normally.
def close_application(window) -> None:
    window.close()



# Confirm that the selected application window no longer exists.
def verify_application_closed(window) -> None:
    window.wait_not("exists", timeout=10)



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
