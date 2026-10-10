"""Open Notepad and interact with its editor through Windows UI Automation."""

def open_notepad():
    from pywinauto.application import Application

    app = Application(backend="uia").start("notepad.exe")
    window = app.window(class_name="Notepad")
    window.wait("visible", timeout=10)
    return window


def write_text(window, text: str) -> None:
    editor = window.child_window(control_type="Edit")
    editor.wait("visible", timeout=5)
    editor.set_edit_text(text)
    if editor.get_value() != text:
        raise RuntimeError("Notepad text could not be verified")


def verify_notepad(window, expected_text: str | None) -> None:
    if not window.is_visible():
        raise RuntimeError("Notepad window is not visible")
    if expected_text is not None:
        editor = window.child_window(control_type="Edit")
        if editor.get_value() != expected_text:
            raise RuntimeError("Notepad text does not match the plan")
