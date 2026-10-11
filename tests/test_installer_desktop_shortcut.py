"""Guard the optional Desktop icon contract in the Inno Setup script.

The desktop link must point to the packaged GUI executable, not python.exe,
and use the executable's embedded application icon.
"""
from pathlib import Path
import unittest

INSTALLER = Path(__file__).resolve().parents[1] / "installer" / "SeirenEmoteController.iss"


class InstallerDesktopShortcutTests(unittest.TestCase):
    def test_desktop_shortcut_is_selected_by_default(self):
        script = INSTALLER.read_text(encoding="utf-8")
        task = next(
            line for line in script.splitlines()
            if line.startswith('Name: "desktopicon";')
        )
        self.assertIn('Description: "Create a desktop shortcut"', task)
        self.assertNotIn("unchecked", task.casefold())

    def test_shortcut_uses_packaged_executable_and_embedded_icon(self):
        script = INSTALLER.read_text(encoding="utf-8")
        link = next(
            line for line in script.splitlines()
            if line.startswith('Name: "{autodesktop}\\{#MyAppName}";')
        )
        executable = '"{app}\\{#MyAppExeName}"'
        self.assertIn('Filename: ' + executable, link)
        self.assertIn('IconFilename: ' + executable, link)
        self.assertIn("Tasks: desktopicon", link)
        self.assertNotIn("python.exe", link.casefold())


if __name__ == "__main__":
    unittest.main()
