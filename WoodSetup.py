"""One-file Windows setup and installed uninstaller, with a CLI for deployment."""
import argparse
import json
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from setup_core import VERSION, install, uninstall
from steam_setup import find_games

BG, PANEL, FG, MUTED, ACCENT = '#111b25', '#1b2936', '#e4edf4', '#9bb0c1', '#58dec1'


def payload_dir():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'payload'


def register(game, remove=False):
    import winreg
    import hashlib
    keypath = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\WoodTUNG_' + hashlib.sha256(str(game).encode()).hexdigest()[:12]
    if remove:
        try: winreg.DeleteKey(winreg.HKEY_CURRENT_USER, keypath)
        except FileNotFoundError: pass
        return
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, keypath) as key:
        values = {'DisplayName': 'Wood for TUNG', 'DisplayVersion': VERSION, 'Publisher': 'Wood contributors',
                  'InstallLocation': str(game), 'UninstallString': f'"{game / "WoodUninstall.exe"}" --uninstall --game-dir "{game}"',
                  'DisplayIcon': str(game / 'WoodLauncher.exe')}
        for name, value in values.items(): winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        for name in ('NoModify', 'NoRepair'): winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, 1)


def handoff_uninstall(game, silent=False, report=None):
    # Run a temporary copy so Windows allows removing the installed uninstaller.
    temp = Path(tempfile.mkdtemp(prefix='wood-uninstall-')) / 'WoodUninstall.exe'
    shutil.copy2(sys.executable, temp)
    args = [str(temp), '--uninstall', '--worker', '--game-dir', str(game)]
    if silent: args.append('--silent')
    if report: args += ['--report', str(report)]
    subprocess.Popen(args, cwd=temp.parent)


from setup_ui import SetupWindow, ACCENT, MUTED


class Setup(SetupWindow):
    def __init__(self, args):
        super().__init__(args, VERSION, find_games())
        self.jobs = queue.Queue()

    def browse(self):
        path = filedialog.askdirectory(title='Choose your TUNG installation', parent=self)
        if path: self.path.set(path)

    def run(self):
        game = Path(self.path.get()).resolve()
        self.set_busy(True)
        self.status.configure(text='Restoring your installationâ€¦' if self.args.uninstall else 'Verifying and installing Woodâ€¦')
        steam_enabled = self.steam.get()
        def work():
            try:
                if self.args.uninstall:
                    conflicts = uninstall(game)
                    if not conflicts: register(game, remove=True)
                    message = 'Wood removed. Your mods and settings remain.'
                    if conflicts: message = 'Modified files were preserved. Details: ' + ', '.join(conflicts)
                else:
                    install(game, payload_dir(), sys.executable, steam_enabled)
                    register(game)
                    message = 'Installed. Reopen Steam, launch TUNG, and press F10 for mods.'
                self.jobs.put((True, message, game))
            except Exception as error: self.jobs.put((False, str(error), game))
        threading.Thread(target=work, daemon=True).start()
        self.after(100, self.finish)

    def finish(self):
        try: ok, message, game = self.jobs.get_nowait()
        except queue.Empty:
            self.after(100, self.finish); return
        self.set_busy(False)
        self.status.configure(text=message, fg=ACCENT if ok else '#ffaf9e')
        self.set_step(2 if ok else 0)
        self.stage.configure(text='ALL SET' if ok else 'NEEDS ATTENTION', fg=ACCENT if ok else '#ffaf9e')
        self.button.configure(state='normal', text='Finish' if ok else 'Try again', command=self.destroy if ok else self.run)


def main():
    if getattr(sys, 'frozen', False) and Path(sys.executable).stem.lower() == 'woodlauncher':
        import WoodLauncher
        WoodLauncher.main()
        return
    parser = argparse.ArgumentParser(description='Wood for TUNG setup')
    parser.add_argument('--game-dir', type=Path)
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--silent', action='store_true')
    parser.add_argument('--no-steam', action='store_true')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--verify-payload', action='store_true')
    args = parser.parse_args()
    if Path(sys.executable).stem.lower() == 'wooduninstall': args.uninstall = True
    if args.uninstall and args.game_dir is None:
        args.game_dir = Path(sys.executable).parent
    if args.uninstall and getattr(sys, 'frozen', False) and not args.worker:
        handoff_uninstall(args.game_dir, args.silent, args.report); return
    if args.verify_payload:
        from setup_core import digest
        from wood_runtime import RUNTIME_SHA256
        result = {'version': VERSION, 'runtime_valid': digest(payload_dir() / 'UE4SS.zip') == RUNTIME_SHA256,
                  'launcher_present': __import__('importlib.util', fromlist=['find_spec']).find_spec('WoodLauncher') is not None}
        if args.report: args.report.write_text(json.dumps(result))
        if not all([result['runtime_valid'], result['launcher_present']]): raise RuntimeError('Payload invalid.')
        return
    if args.silent:
        if not args.game_dir: parser.error('--silent requires --game-dir')
        if args.uninstall:
            conflicts = uninstall(args.game_dir)
            if not conflicts: register(args.game_dir, True)
            result = {'success': not conflicts, 'preserved': conflicts}
        else:
            install(args.game_dir, payload_dir(), sys.executable, not args.no_steam)
            register(args.game_dir); result = {'success': True, 'version': VERSION}
        if args.report: args.report.write_text(json.dumps(result))
        return
    Setup(args).mainloop()


if __name__ == '__main__':
    try: main()
    except Exception as error:
        if '--report' in sys.argv:
            Path(sys.argv[sys.argv.index('--report') + 1]).write_text(json.dumps({'success': False, 'error': str(error)}))
        elif '--silent' not in sys.argv:
            messagebox.showerror('Wood setup', str(error))
        sys.exit(1)
