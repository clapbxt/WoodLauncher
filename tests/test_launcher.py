import unittest

from WoodLauncher import STEAM_URI, launch_game


class LauncherTests(unittest.TestCase):
    def test_launches_tung_through_steam_protocol(self):
        opened = []
        launch_game(opened.append)
        self.assertEqual(opened, [STEAM_URI])

    def test_reports_protocol_launch_failures_to_caller(self):
        def fail(_uri):
            raise OSError("Steam is unavailable")

        with self.assertRaisesRegex(OSError, "Steam is unavailable"):
            launch_game(fail)


if __name__ == "__main__":
    unittest.main()
