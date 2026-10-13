"""Wood Launcher: update Wood, then start TUNG through Steam."""
import argparse
from pathlib import Path
import queue
import json
import sys
import tempfile
import threading
import tkinter as tk
import base64
import os
from tkinter import filedialog, messagebox, ttk

from launcher_core import LAUNCHER_VERSION, RELEASE_MANIFEST, download_update, launch_game, release_info, update_available
from steam_discovery import find_games


class Launcher(tk.Tk):
    def __init__(self, game_dir=None):
        super().__init__()
        self.title('Wood Launcher')
        self.geometry('560x350')
        self.resizable(False, False)
        self.configure(bg='#101017')
        games = find_games()
        self.game = tk.StringVar(value=str(game_dir or (games[0] if games else '')))
        self.status = tk.StringVar(value='Ready to start TUNG.')
        self.jobs = queue.Queue()
        tk.Label(self, text='wood', bg='#101017', fg='#f4f2fc', font=('Segoe UI', 32, 'bold')).pack(pady=(25, 0))
        tk.Label(self, text=f'Wood Launcher  ·  v{LAUNCHER_VERSION}', bg='#101017', fg='#a688fa', font=('Segoe UI', 10)).pack()
        tk.Label(self, text='TUNG installation', bg='#101017', fg='#aaa7be', font=('Segoe UI', 10)).pack(anchor='w', padx=42, pady=(28, 5))
        row = tk.Frame(self, bg='#101017'); row.pack(fill='x', padx=42)
        ttk.Entry(row, textvariable=self.game).pack(side='left', fill='x', expand=True, ipady=7)
        ttk.Button(row, text='Browse…', command=self.browse).pack(side='left', padx=(8, 0))
        tk.Label(self, textvariable=self.status, bg='#101017', fg='#aaa7be', wraplength=470, justify='left').pack(anchor='w', padx=42, pady=(20, 10))
        self.progress = ttk.Progressbar(self, mode='indeterminate', length=470)
        self.start = ttk.Button(self, text='Play TUNG  →', command=self.begin); self.start.pack(anchor='e', padx=42, pady=12)
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.after(150, self.check_updates)

    def browse(self):
        chosen = filedialog.askdirectory(title='Choose your TUNG installation', parent=self)
        if chosen: self.game.set(chosen)

    def begin(self):
        self.start.configure(state='disabled')
        self.progress.pack(padx=42, pady=(0, 15)); self.progress.start(12)
        self.status.set('Checking for Wood updates…')
        threading.Thread(target=self._check_update, daemon=True).start()
        self.after(100, self.finish_check)

    def check_updates(self):
        self.begin()

    def _check_update(self):
        try: self.jobs.put((True, release_info(RELEASE_MANIFEST)))
        except Exception as error: self.jobs.put((False, error))

    def finish_check(self):
        try: ok, value = self.jobs.get_nowait()
        except queue.Empty:
            self.after(100, self.finish_check); return
        self.progress.stop(); self.progress.pack_forget(); self.start.configure(state='normal')
        if not ok:
            self.status.set('Could not check updates. You can still play TUNG.')
            messagebox.showwarning('Wood update check', f'Update check failed: {value}\n\nTUNG will still start.', parent=self)
            self.play(); return
        release = value
        try: update = update_available(release)
        except (ValueError, TypeError): update = False
        if update:
            if messagebox.askyesno('Wood update available', f"Wood Launcher {release['version']} / Wood {release['wood_version']} is available. Download and install it now?\n\nTUNG will start after the update finishes.", parent=self):
                self.start.configure(state='disabled'); self.status.set('Downloading and verifying Wood…')
                self.progress.pack(padx=42, pady=(0, 15)); self.progress.start(12)
                threading.Thread(target=self._download, args=(release,), daemon=True).start()
                self.after(100, self.finish_download); return
        self.play()

    def _download(self, release):
        try: self.jobs.put((True, download_update(release)))
        except Exception as error: self.jobs.put((False, error))

    def finish_download(self):
        try: ok, value = self.jobs.get_nowait()
        except queue.Empty:
            self.after(100, self.finish_download); return
        self.progress.stop(); self.progress.pack_forget(); self.start.configure(state='normal')
        if not ok:
            messagebox.showerror('Wood update failed', f'{value}\n\nTUNG will start with the installed version.', parent=self)
            self.play(); return
        installer, launcher_update = value
        self.status.set('Installing Wood… TUNG will start when setup finishes.')
        self.withdraw()
        try:
            import subprocess, time
            report = Path(tempfile.gettempdir()) / 'wood-update-report.json'
            report.unlink(missing_ok=True)
            subprocess.Popen([str(installer), '--silent', '--game-dir', str(Path(self.game.get()).resolve()),
                              '--report', str(report)], cwd=installer.parent)
            deadline = time.monotonic() + 240
            while time.monotonic() < deadline and not report.is_file():
                time.sleep(0.25)
            outcome = json.loads(report.read_text(encoding='utf-8')) if report.is_file() else {'success': False, 'error': 'Installer timed out.'}
            if not outcome.get('success'):
                messagebox.showerror('Wood update failed', outcome.get('error', 'Installer did not complete successfully.'), parent=self)
                self.status.set('Update did not finish. Choose Play to check again, or close Wood Launcher.')
                self.start.configure(text='Retry update  →', command=self.begin, state='normal')
                return
            game = Path(self.game.get()).resolve()
            target = game / 'WoodLauncher.exe'
            replacement = target.with_suffix('.new')
            def ps_literal(value): return "'" + str(value).replace("'", "''") + "'"
            script = ("$ErrorActionPreference='Stop'; "
                      "$parent=[int]$env:WOOD_LAUNCHER_PARENT; "
                      "while(Get-Process -Id $parent -ErrorAction SilentlyContinue){Start-Sleep -Milliseconds 250}; "
                      f"Copy-Item -LiteralPath {ps_literal(launcher_update)} -Destination {ps_literal(replacement)} -Force; "
                      f"Move-Item -LiteralPath {ps_literal(replacement)} -Destination {ps_literal(target)} -Force; "
                      f"Start-Process -FilePath {ps_literal(target)} -ArgumentList @('--game-dir',{ps_literal(game)})")
            encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
            environment = dict(os.environ, WOOD_LAUNCHER_PARENT=str(os.getpid()))
            subprocess.Popen(['powershell.exe', '-NoProfile', '-WindowStyle', 'Hidden',
                              '-EncodedCommand', encoded], env=environment,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            return
        except Exception as error:
            messagebox.showerror('Wood update failed', str(error), parent=self)
            self.status.set('Update did not finish. Choose Play to check again, or close Wood Launcher.')
            self.start.configure(text='Retry update  →', command=self.begin, state='normal')
            return
        self.destroy()
        launch_game(self.game.get())

    def play(self):
        try:
            launch_game(self.game.get())
            self.destroy()
        except Exception as error:
            messagebox.showerror('Could not start TUNG', str(error), parent=self)


def main():
    parser = argparse.ArgumentParser(description='Wood Launcher for TUNG')
    parser.add_argument('--game-dir', type=Path)
    parser.add_argument('--verify-tk', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.verify_tk:
        smoke = tk.Tk(); smoke.withdraw(); smoke.destroy()
        return
    if args.game_dir is None and Path(sys.executable).stem.lower() == 'woodlauncher':
        candidate = Path(sys.executable).parent
        if (candidate / 'TUNG/Binaries/Win64/TUNG-Win64-Shipping.exe').is_file():
            args.game_dir = candidate
    Launcher(args.game_dir).mainloop()


if __name__ == '__main__': main()
