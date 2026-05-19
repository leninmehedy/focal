import platform
import subprocess


def notify(title: str, body: str) -> None:
    """Send a desktop notification. Silently no-ops if not supported."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{body}" with title "{title}"',
                ],
                capture_output=True,
                timeout=5,
            )
        elif system == "Linux":
            subprocess.run(["notify-send", title, body], capture_output=True, timeout=5)
    except Exception:
        pass  # Never let notification failure break sync
