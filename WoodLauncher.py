#!/usr/bin/env python3
"""Wood launcher: manage native Unreal mods without a desktop game overlay."""
from __future__ import annotations

import argparse
import ast
import ctypes
from ctypes import wintypes
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox

from wood_runtime import BASE, BIN, DATA, RUNTIME, Bridge, atomic_write, installed, install_runtime, load_json, valid_speed

CONFIG_FILE = BASE / 'wood_config.json'
GAME = BIN / 'TUNG-Win64-Shipping.exe'
DATA.mkdir(exist_ok=True)
logging.basicConfig(filename=DATA / 'launcher.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
BG = '#101017'
PANEL = '#191922'
FG = '#f4f2fc'
MUTED = '#aaa7be'
ACCENT = '#c4f46b'


def game_running():
    if Bridge().status().get('connected'):
        return True
    # tasklist depends on services/credentials and can fail under restricted
    # tokens. Toolhelp enumerates processes directly without launching a shell.
    class Entry(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('usage', wintypes.DWORD), ('pid', wintypes.DWORD),
                    ('heap', ctypes.c_size_t), ('module', wintypes.DWORD), ('threads', wintypes.DWORD),
                    ('parent', wintypes.DWORD), ('priority', wintypes.LONG), ('flags', wintypes.DWORD),
                    ('name', wintypes.WCHAR * 260)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    for method in ('Process32FirstW', 'Process32NextW'):
        fn = getattr(kernel, method)
        fn.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
        fn.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    entry = Entry()
    entry.size = ctypes.sizeof(entry)
    try:
        more = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while more:
            if entry.name.lower() == GAME.name.lower(): return True
            more = kernel.Process32NextW(snapshot, ctypes.byref(entry))
        return False
    finally:
        kernel.CloseHandle(snapshot)


def discover_mods():
    """Read manifests without executing disabled or untrusted Python modules."""
    mods = []
    for manifest in sorted((BASE / 'NativeMods').glob('*/manifest.json')):
        if manifest.parent.name.startswith('_'): continue
        info = load_json(manifest, {})
        if info.get('id'):
            mods.append({**info, 'path': manifest.parent, 'state': 'Native'})
    for path in sorted((BASE / 'Mods').glob('*.py')):
        if path.name.startswith('_'):
            continue
        info = {'id': path.stem, 'name': path.stem, 'version': '?'}
        try:
            for node in ast.parse(path.read_text(encoding='utf-8-sig')).body:
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '__manifest__' for t in node.targets):
                    info.update(ast.literal_eval(node.value))
                    break
            info.update(path=path, state='Legacy Python', id=path.stem)
        except (OSError, SyntaxError, ValueError, TypeError) as error:
            info.update(path=path, state='Manifest error', description=str(error))
        mods.append(info)
    return mods


def launch_game(command=None):
    if game_running():
        raise RuntimeError('TUNG is already running. Use F10 to open its mod menu.')
    install_runtime()
    cmd = list(command) if command else [str(GAME)]
    if not cmd:
        raise ValueError('No game command supplied.')
    logging.info('Launching game: %r', cmd)
    return subprocess.Popen(cmd, cwd=str(BASE))


class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        icon = Path(getattr(sys, '_MEIPASS', BASE)) / 'wood.ico'
        if icon.exists(): self.iconbitmap(str(icon))
        self.bridge = Bridge()
        self.config = load_json(CONFIG_FILE, {'mods_disabled': []})
        self.title('Wood | TUNG Mod Launcher')
        self.geometry('1050x800')
        self.minsize(950, 740)
        self.configure(bg=BG)
        self.pending = None
        self.pending_since = None
        self._slider_job = None
        self._style()
        self._build()
        self.refresh()
        self.after(300, self.poll)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', background=PANEL, foreground=FG, font=('Segoe UI', 10))
        style.configure('TButton', padding=(14, 9), background='#292737', borderwidth=0)
        style.map('TButton', background=[('active', '#39334d')], foreground=[('disabled', MUTED)])
        style.configure('Accent.TButton', background=ACCENT, foreground=BG, font=('Segoe UI', 10, 'bold'))
        style.map('Accent.TButton', background=[('active', '#d6ff91')])
        style.configure('Treeview', background=PANEL, fieldbackground=PANEL, foreground=FG, rowheight=38, borderwidth=0)
        style.configure('Treeview.Heading', background='#272332', foreground=MUTED, padding=9)
        style.map('Treeview', background=[('selected', '#493568')])
        style.configure('TEntry', fieldbackground=BG, foreground=FG, insertcolor=FG, bordercolor='#3b374b', padding=(10, 8))
        style.configure('TCheckbutton', background=PANEL, foreground=FG, indicatorbackground=BG, indicatorforeground=ACCENT)
        style.configure('TScale', troughcolor='#39304d', background=PANEL)

    def label(self, parent, text='', size=10, color=FG, **kwargs):
        return tk.Label(parent, text=text, bg=parent.cget('bg'), fg=color,
                        font=('Segoe UI', size), **kwargs)

    def _build(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill='x', padx=28, pady=(22, 16))
        self.label(header, 'WOOD', 29, ACCENT).pack(side='left')
        self.label(header, 'TUNG / 2.2.0', 12, MUTED).pack(side='left', padx=18)
        self.connection = self.label(header, 'Runtime offline', 11, MUTED)
        self.connection.pack(side='right')
        toolbar = tk.Frame(self, bg=BG)
        toolbar.pack(fill='x', padx=28, pady=(0, 18))
        self.launch_button = ttk.Button(toolbar, text='Launch modded TUNG', style='Accent.TButton', command=self.launch)
        self.launch_button.pack(side='left')
        ttk.Button(toolbar, text='Update native mods', command=self.install).pack(side='left', padx=10)
        ttk.Button(toolbar, text='Open Mods folder', command=lambda: os.startfile(BASE / 'NativeMods')).pack(side='left')
        ttk.Button(toolbar, text='Refresh', command=self.refresh).pack(side='right')
        content = tk.Frame(self, bg=BG)
        content.pack(fill='both', expand=True, padx=28)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)
        left = tk.Frame(content, bg=PANEL, padx=16, pady=16)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 12))
        self.label(left, 'Mod library', 17).pack(anchor='w', pady=(0, 12))
        self.search = tk.StringVar()
        search = ttk.Entry(left, textvariable=self.search)
        search.pack(fill='x', pady=(0, 12), ipady=5)
        search.insert(0, '')
        self.label(left, 'Search installed mods by name', 9, MUTED).pack(anchor='w', pady=(0, 8))
        self.search.trace_add('write', lambda *_: self.filter_mods())
        self.tree = ttk.Treeview(left, columns=('version', 'state'), show='tree headings', selectmode='browse')
        self.tree.heading('#0', text='MOD')
        self.tree.heading('version', text='VERSION')
        self.tree.heading('state', text='TYPE')
        self.tree.column('#0', width=170, stretch=True)
        self.tree.column('version', width=72, stretch=False)
        self.tree.column('state', width=110, stretch=False)
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.select)
        toggle = ttk.Button(left, text='Enable / disable selected mod', command=self.toggle_selected)
        toggle.pack(before=self.tree, side='bottom', fill='x', pady=(12, 0))
        self.detail = self.label(left, '', 10, MUTED, wraplength=365, justify='left', anchor='w')
        self.detail.pack(before=toggle, side='bottom', fill='x', pady=(14, 0))
        right = tk.Frame(content, bg=PANEL, padx=24, pady=20)
        right.grid(row=0, column=1, sticky='nsew')
        self.label(right, 'Time Warp', 22).pack(anchor='w')
        self.label(right, 'Native world-speed control', 11, MUTED).pack(anchor='w', pady=(2, 12))
        self.speed = tk.DoubleVar(value=self.saved_settings().get('speed', 1))
        self.readout = self.label(right, f'{self.speed.get():.2f}x', 34, ACCENT)
        self.readout.pack(anchor='w', pady=(6, 0))
        self.actual = self.label(right, 'Start TUNG to apply changes', 10, MUTED)
        self.actual.pack(anchor='w', pady=(0, 12))
        self.scale = ttk.Scale(right, from_=0.05, to=4, variable=self.speed, command=self.slider_changed)
        self.scale.pack(fill='x', pady=10)
        presets = tk.Frame(right, bg=PANEL)
        presets.pack(fill='x', pady=(0, 18))
        for value in (0.1, 0.25, 0.5, 1, 2, 4):
            ttk.Button(presets, text=f'{value:g}x', width=4, command=lambda v=value: self.set_speed(v)).pack(side='left', padx=(0, 3))
        self.enabled = tk.BooleanVar(value=self.saved_settings().get('enabled', True))
        ttk.Checkbutton(right, text='Enable Time Warp', variable=self.enabled,
                        command=lambda: self.setting('enabled', self.enabled.get())).pack(anchor='w', pady=8)
        self.travel = tk.BooleanVar(value=self.saved_settings().get('restore_on_travel', True))
        ttk.Checkbutton(right, text='Reset speed when the world changes', variable=self.travel,
                        command=lambda: self.setting('restore_on_travel', self.travel.get())).pack(anchor='w', pady=8)
        ttk.Button(right, text='Open in-game mod menu  ·  F10', command=lambda: self.command('menu')).pack(fill='x', pady=(16, 8))
        ttk.Button(right, text='Reset to normal speed', command=lambda: self.set_speed(1)).pack(fill='x')
        self.label(right, 'F6  slower     F7  normal     F8  faster\n\nSettings and buttons render inside TUNG.\nNo address calibration is needed.',
                   10, MUTED, justify='left').pack(anchor='w', pady=(12, 0))
        footer = tk.Frame(self, bg=BG)
        footer.pack(before=content, side='bottom', fill='x', padx=28, pady=12)
        self.notice = self.label(footer, 'Ready', 10, MUTED, anchor='w', wraplength=780)
        self.notice.pack(side='left', fill='x', expand=True)
        ttk.Button(footer, text='Logs', command=lambda: os.startfile(DATA)).pack(side='right')

    def saved_settings(self):
        result = {'speed': 1.0, 'enabled': True, 'restore_on_travel': True}
        try:
            for line in (DATA / 'settings.ini').read_text().splitlines():
                key, _, value = line.partition('=')
                if key == 'speed': result[key] = valid_speed(value)
                elif key in result: result[key] = value == 'true'
        except (OSError, ValueError):
            pass
        return result

    def refresh(self):
        self.config = load_json(CONFIG_FILE, {'mods_disabled': []})
        self.mods = discover_mods()
        self.filter_mods()
        self.notice.config(text='Native runtime installed · F10 opens the in-game menu' if installed() else 'Run WoodSetup.exe to install the native runtime')

    def filter_mods(self):
        if not hasattr(self, 'mods'): return
        for item in self.tree.get_children(): self.tree.delete(item)
        query = self.search.get().strip().lower()
        for mod in self.mods:
            if query and query not in (mod['name'] + ' ' + mod['id']).lower(): continue
            if mod['id'] in self.config.get('mods_disabled', []) and mod['state'] == 'Native': mod['state'] = 'Disabled'
            self.tree.insert('', 'end', iid=mod['id'], text=mod['name'], values=(mod.get('version', '?'), mod['state']))
        if self.tree.exists('TimeWarp'):
            self.tree.selection_set('TimeWarp')
            self.select()

    def select(self, _event=None):
        selected = self.tree.selection()
        if not selected: return
        mod = next(m for m in self.mods if m['id'] == selected[0])
        description = mod.get('description', '')
        if mod['state'] == 'Legacy Python':
            description += '\n\nLegacy overlay mod: kept on disk, not executed by the native runtime.'
        self.detail.config(text=description)

    def toggle_selected(self):
        selected = self.tree.selection()
        if not selected: return
        mod_id = selected[0]
        if mod_id == 'TimeWarp':
            self.enabled.set(not self.enabled.get())
            self.setting('enabled', self.enabled.get())
            return
        mod = next(m for m in self.mods if m['id'] == mod_id)
        if mod['state'] == 'Legacy Python':
            self.notice.config(text='Legacy overlay mods need a native Lua port. See NativeMods/_Example.')
            return
        disabled = set(self.config.get('mods_disabled', []))
        if mod_id in disabled: disabled.remove(mod_id)
        else: disabled.add(mod_id)
        self.config['mods_disabled'] = sorted(disabled)
        atomic_write(CONFIG_FILE, json.dumps(self.config, indent=2))
        self.refresh()
        self.notice.config(text='Mod selection saved. Changes take effect on the next game launch.')

    def slider_changed(self, value):
        self.readout.config(text=f'{float(value):.2f}x')
        if self._slider_job: self.after_cancel(self._slider_job)
        self._slider_job = self.after(180, lambda: self.set_speed(float(value)))

    def set_speed(self, value):
        if self._slider_job: self.after_cancel(self._slider_job)
        self._slider_job = None
        value = valid_speed(value)
        self.speed.set(value)
        self.readout.config(text=f'{value:.2f}x')
        self.setting('speed', value)

    def setting(self, key, value):
        if self.bridge.status().get('connected'):
            self.command(key, value)
        else:
            settings = self.saved_settings()
            settings[key] = value
            atomic_write(DATA / 'settings.ini', '\n'.join(f'{k}={str(v).lower()}' for k, v in settings.items()) + '\n')
            self.notice.config(text='Saved for next launch. World changes reset speed if enabled above.')

    def command(self, action, value=''):
        if not self.bridge.status().get('connected'):
            self.notice.config(text='Start modded TUNG first; runtime is offline.')
            return
        self.pending = self.bridge.send(action, value)
        self.pending_since = time.monotonic()
        self.notice.config(text='Waiting for the game to confirm…')

    def poll(self):
        status = self.bridge.status()
        connected = status.get('connected')
        self.connection.config(text='Runtime connected' if connected else 'Runtime offline', fg=ACCENT if connected else MUTED)
        if connected:
            self.actual.config(text=f"Engine confirms {status.get('applied', 1):.2f}x")
            if not self.pending:
                self.enabled.set(status.get('enabled', True))
                self.travel.set(status.get('restore_on_travel', self.travel.get()))
            if not self._slider_job and not self.pending:
                self.speed.set(status.get('speed', 1))
                self.readout.config(text=f"{self.speed.get():.2f}x")
            if self.pending and str(status.get('ack')) == str(self.pending):
                self.pending = None
                self.notice.config(text='Applied by TUNG' if not status.get('error') else status['error'])
            if status.get('error'): self.notice.config(text=status['error'])
        else:
            self.actual.config(text='Start TUNG to apply changes')
        if self.pending and time.monotonic() - self.pending_since > 5:
            self.pending = None
            self.notice.config(text='The game did not confirm the change. Check the runtime log.')
        self.after(500, self.poll)

    def install(self):
        try:
            if game_running(): raise RuntimeError('Close TUNG before updating native mod files.')
            install_runtime()
            self.refresh()
            self.notice.config(text='Native mod updated. Launch TUNG and press F10.')
        except Exception as error: self.report(error)

    def launch(self):
        try:
            launch_game()
            self.notice.config(text='Starting TUNG. Press F10 for mods once the world is ready.')
        except Exception as error: self.report(error)

    def report(self, error):
        logging.exception('Launcher action failed')
        self.notice.config(text=str(error))
        messagebox.showerror('Wood launcher', str(error), parent=self)


def main():
    parser = argparse.ArgumentParser(description='Wood native mod launcher')
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--overlay', action='store_true', help='Compatibility alias for --launch; uses native menu')
    parser.add_argument('--self-test', action='store_true', help='Request engine time-dilation checks in a running game')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.install:
        print(install_runtime())
    elif args.self_test:
        bridge = Bridge()
        if not bridge.status().get('connected'): raise RuntimeError('Start modded TUNG first.')
        print('Requested engine self-test:', bridge.send('selftest'))
    elif args.launch or args.overlay:
        command = args.command
        if command and command[0] == '--': command = command[1:]
        proc = launch_game(command or None)
        # Steam's bootstrapper can exit before the shipping process appears.
        # Keep the wrapper alive for Steam's session tracking.
        deadline = time.monotonic() + 90
        found_game = False
        while time.monotonic() < deadline or found_game:
            running = game_running()
            if running:
                found_game = True
            elif found_game:
                break
            elif proc.poll() is not None and proc.returncode:
                raise RuntimeError(f'TUNG exited with code {proc.returncode}. See .wood/launcher.log.')
            time.sleep(2)
    else:
        Launcher().mainloop()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logging.exception('Wood failed')
        messagebox.showerror('Wood launcher', 'Wood could not complete this action. See .wood/launcher.log for details.')
        sys.exit(1)
