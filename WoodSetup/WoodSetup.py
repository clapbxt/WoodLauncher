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
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from setup_core import VERSION, install, uninstall
from process_launch import external_popen
from steam_setup import find_games
from update_core import (download_setup, game_is_running, launch_game,
                         release_info, update_available)

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
                  'DisplayIcon': str(game / 'WoodUninstall.exe')}
        for name, value in values.items(): winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        for name in ('NoModify', 'NoRepair'): winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, 1)


def handoff_uninstall(game, silent=False, report=None):
    # Run a temporary copy so Windows allows removing the installed uninstaller.
    temp = Path(tempfile.mkdtemp(prefix='wood-uninstall-')) / 'WoodUninstall.exe'
    shutil.copy2(sys.executable, temp)
    args = [str(temp), '--uninstall', '--worker', '--game-dir', str(game)]
    if silent: args.append('--silent')
    if report: args += ['--report', str(report)]
    external_popen(args, cwd=temp.parent)


def check_for_setup_update(game_dir=None):
    """When Setup is re-run, hand off to the newest verified Setup first."""
    try:
        release = release_info()
        if not update_available(release, VERSION):
            return False
    except Exception:
        return False
    prompt = tk.Tk(); prompt.withdraw()
    yes = messagebox.askyesno('Wood update available',
        f"Wood {release['wood_version']} is available. Download the latest setup now?", parent=prompt)
    prompt.destroy()
    if not yes:
        return False
    progress = tk.Tk(); progress.title('Wood Setup update'); progress.geometry('380x110')
    progress.resizable(False, False)
    tk.Label(progress, text='Downloading and verifying the latest Wood Setup…',
             font=('Segoe UI', 10)).pack(pady=(22, 10))
    bar = ttk.Progressbar(progress, mode='indeterminate', length=320)
    bar.pack(); bar.start(12); progress.update_idletasks()
    try:
        setup = download_setup(release)
    finally:
        bar.stop(); progress.destroy()
    command = [str(setup)]
    if game_dir:
        command += ['--game-dir', str(game_dir)]
    external_popen(command, cwd=setup.parent)
    return True


def check_for_game_update(game_dir):
    """Called by WoodRuntime on TUNG boot; updater waits for a safe game exit."""
    try:
        release = release_info()
        if not update_available(release, VERSION):
            return
    except Exception:
        return  # Offline boot should not interrupt play.

    window = tk.Tk()
    window.withdraw()
    yes = messagebox.askyesno('Wood update available',
        f"Wood {release['wood_version']} is available. Download it now?\n\n"
        'If you continue, the update will install after you exit TUNG, then TUNG will reopen.',
        parent=window)
    if not yes:
        window.destroy()
        return
    window.deiconify()
    window.title('Wood updater')
    window.geometry('440x140')
    window.resizable(False, False)
    tk.Label(window, text='Downloading and verifying Wood…', font=('Segoe UI', 12)).pack(pady=(22, 12))
    bar = ttk.Progressbar(window, mode='indeterminate', length=370)
    bar.pack(); bar.start(12)
    jobs = queue.Queue()
    def work():
        try: jobs.put((True, download_setup(release)))
        except Exception as error: jobs.put((False, error))
    threading.Thread(target=work, daemon=True).start()
    def poll_download():
        try: ok, value = jobs.get_nowait()
        except queue.Empty:
            window.after(150, poll_download); return
        bar.stop(); window.destroy()
        if ok:
            external_popen([str(value), '--install-after-exit', '--game-dir', str(Path(game_dir).resolve())],
                             cwd=value.parent)
        else:
            failed = tk.Tk(); failed.withdraw()
            messagebox.showerror('Wood update failed', str(value), parent=failed)
            failed.destroy()
    window.after(150, poll_download)
    window.mainloop()


def install_after_game_exit(game_dir):
    """Wait for TUNG to exit, install from this fresh Setup copy, and reopen it."""
    game = Path(game_dir).resolve()
    window = tk.Tk()
    window.title('Wood updater')
    window.geometry('500x170')
    window.resizable(False, False)
    tk.Label(window, text='Update downloaded and verified', font=('Segoe UI', 13, 'bold')).pack(pady=(22, 8))
    tk.Label(window, text='Exit TUNG when you are ready. Wood will install and reopen the game.',
             wraplength=440, justify='center').pack(pady=5)
    bar = ttk.Progressbar(window, mode='indeterminate', length=420)
    bar.pack(pady=14); bar.start(12)
    jobs = queue.Queue()
    def work():
        try:
            while game_is_running():
                time.sleep(1)
            time.sleep(4)  # Allow the game's last status write to settle.
            install(game, payload_dir(), sys.executable)
            register(game)
            launch_game(game)
            jobs.put((True, None))
        except Exception as error:
            jobs.put((False, str(error)))
    threading.Thread(target=work, daemon=True).start()
    def poll():
        try: ok, error = jobs.get_nowait()
        except queue.Empty:
            window.after(500, poll); return
        bar.stop(); window.destroy()
        if not ok:
            failed = tk.Tk(); failed.withdraw()
            messagebox.showerror('Wood update failed', error, parent=failed)
            failed.destroy()
    window.protocol('WM_DELETE_WINDOW', lambda: None)
    window.after(500, poll)
    window.mainloop()


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
        self.status.configure(text='Restoring your installation…' if self.args.uninstall else 'Verifying and installing Wood…')
        def work():
            try:
                if self.args.uninstall:
                    conflicts = uninstall(game)
                    if not conflicts: register(game, remove=True)
                    message = 'Wood removed. Your mods and settings remain.'
                    if conflicts: message = 'Wood was removed, but some files could not be restored. Details: ' + ', '.join(conflicts)
                else:
                    install(game, payload_dir(), sys.executable)
                    register(game)
                    message = 'Installed. Launch TUNG via Steam and press F10 for mods.'
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
    parser = argparse.ArgumentParser(description='Wood for TUNG setup')
    parser.add_argument('--game-dir', type=Path)
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--silent', action='store_true')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--verify-payload', action='store_true')
    parser.add_argument('--check-updates', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--install-after-exit', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--speedrun-mode', choices=('on', 'off'), help=argparse.SUPPRESS)
    parser.add_argument('--restart-token', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.speedrun_mode:
        if not args.game_dir or not args.restart_token:
            parser.error('--speedrun-mode requires --game-dir and --restart-token')
        from speedrun_core import restart_for_mode
        restart_for_mode(args.game_dir, args.speedrun_mode == 'on', args.restart_token)
        return
    if args.check_updates:
        if not args.game_dir: parser.error('--check-updates requires --game-dir')
        check_for_game_update(args.game_dir); return
    if args.install_after_exit:
        if not args.game_dir: parser.error('--install-after-exit requires --game-dir')
        install_after_game_exit(args.game_dir); return
    if Path(sys.executable).stem.lower() == 'wooduninstall': args.uninstall = True
    if args.uninstall and args.game_dir is None:
        args.game_dir = Path(sys.executable).parent
    if args.uninstall and getattr(sys, 'frozen', False) and not args.worker:
        handoff_uninstall(args.game_dir, args.silent, args.report); return
    if args.verify_payload:
        from setup_core import digest
        from wood_runtime import RUNTIME_SHA256
        resource_root = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
        logo_valid = ((resource_root / 'WoodLauncherLogo.png').is_file()
                      or (resource_root / 'payload' / 'WoodLauncherLogo.png').is_file())
        result = {'version': VERSION, 'runtime_valid': digest(payload_dir() / 'UE4SS.zip') == RUNTIME_SHA256,
                  'logo_valid': logo_valid}
        if args.report: args.report.write_text(json.dumps(result))
        if not result['runtime_valid'] or not logo_valid: raise RuntimeError('Installer resources invalid.')
        return
    if args.silent:
        if not args.game_dir: parser.error('--silent requires --game-dir')
        if args.uninstall:
            conflicts = uninstall(args.game_dir)
            if not conflicts: register(args.game_dir, True)
            result = {'success': not conflicts, 'preserved': conflicts}
        else:
            install(args.game_dir, payload_dir(), sys.executable)
            register(args.game_dir); result = {'success': True, 'version': VERSION}
        if args.report: args.report.write_text(json.dumps(result))
        return
    if not args.uninstall and check_for_setup_update(args.game_dir):
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
