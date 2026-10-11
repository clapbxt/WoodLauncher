"""Small Steam protocol launcher; UE4SS loads Wood when TUNG starts."""
from __future__ import annotations

import os
from typing import Callable

STEAM_URI = "steam://run/4341400"


def launch_game(open_uri: Callable[[str], None] | None = None) -> None:
    if open_uri is None:
        open_uri = os.startfile
    open_uri(STEAM_URI)


def main() -> None:
    try:
        launch_game()
    except OSError as error:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None,
            f"Could not start TUNG through Steam.\n\n{error}",
            "Wood Launcher",
            0x10,
        )


if __name__ == "__main__":
    main()
