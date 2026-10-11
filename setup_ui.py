"""Dependency-free desktop presentation for Wood setup and uninstall."""
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk

BG = '#101017'
PANEL = '#191922'
FG = '#f4f2fc'
MUTED = '#aaa7be'
ACCENT = '#c4f46b'
PURPLE = '#a688fa'


class SetupWindow(tk.Tk):
    def __init__(self, args, version, games):
        super().__init__()
        self.args = args
        self.busy = False
        self.title('Wood • Uninstall' if args.uninstall else 'Wood • Setup')
        self.geometry('960x690')
        self.minsize(900, 660)
        self.configure(bg=BG)
        icon = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'wood.ico'
        if icon.exists():
            self.iconbitmap(str(icon))
        self.brand_logo = tk.PhotoImage(file=str(Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'WoodLauncherLogo.png'))
        self.brand_small = self.brand_logo.subsample(2)
        self.iconphoto(True, self.brand_logo)
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', background=PANEL, foreground=FG, font=('Segoe UI', 10))
        style.configure('TButton', background='#292737', foreground=FG, borderwidth=0,
                        padding=(18, 12), focusthickness=2, focuscolor=PURPLE)
        style.map('TButton', background=[('disabled', '#22212e'), ('active', '#39334d')],
                  foreground=[('disabled', '#777488')])
        style.configure('Accent.TButton', background=ACCENT, foreground='#19200f',
                        font=('Segoe UI', 11, 'bold'), padding=(26, 14))
        style.map('Accent.TButton', background=[('disabled', '#454d37'), ('active', '#d6ff91')],
                  foreground=[('disabled', '#aaa7be')])
        style.configure('TEntry', fieldbackground='#101017', foreground=FG,
                        insertcolor=FG, bordercolor='#3b374b', lightcolor='#3b374b',
                        darkcolor='#3b374b', padding=(12, 12), selectbackground='#6944b5')
        style.map('TEntry', bordercolor=[('focus', PURPLE)],
                  fieldbackground=[('disabled', '#22212e')], foreground=[('disabled', MUTED)])
        style.configure('TCheckbutton', background=PANEL, foreground=FG, padding=0,
                        indicatorbackground='#101017', indicatorforeground=ACCENT,
                        indicatorcolor=ACCENT, bordercolor='#615873', focuscolor=PURPLE)
        style.map('TCheckbutton', background=[('active', PANEL)],
                  indicatorbackground=[('selected', '#463366'), ('active', '#30283e')],
                  foreground=[('disabled', '#777488')])
        style.configure('Wood.Horizontal.TProgressbar', troughcolor='#292737',
                        background=ACCENT, borderwidth=0, lightcolor=ACCENT, darkcolor=ACCENT)

        rail = tk.Frame(self, bg='#15141e', width=212)
        rail.pack(side='left', fill='y')
        rail.pack_propagate(False)
        logo = tk.Canvas(rail, width=160, height=70, bg='#15141e', highlightthickness=0)
        logo.pack(padx=26, pady=(30, 24))
        logo.create_image(32, 35, image=self.brand_small)
        logo.create_text(74, 33, text='wood', anchor='w', fill=FG, font=('Segoe UI', 25, 'bold'))
        self.label(rail, 'TUNG MOD TOOLKIT', 9, MUTED).pack(anchor='w', padx=28)
        self.label(rail, f'Setup / {version}', 10, MUTED).pack(anchor='w', padx=28, pady=(6, 42))
        self.steps = []
        for number, name, detail in [('01', 'Configure', 'Choose your game'),
                                     ('02', 'Remove' if args.uninstall else 'Install', 'We handle the rest'),
                                     ('03', 'All set', 'Your next attempt')]:
            box = tk.Frame(rail, bg='#15141e', padx=16, pady=14)
            box.pack(fill='x', padx=12, pady=4)
            self.label(box, number + '  ' + name, 11, FG).pack(anchor='w')
            self.label(box, detail, 9, MUTED).pack(anchor='w', padx=27, pady=(5, 0))
            self.steps.append(box)
        self.set_step(0)
        rail_bottom = tk.Frame(rail, bg='#15141e')
        rail_bottom.pack(side='bottom', fill='x', padx=28, pady=28)
        self.label(rail_bottom, 'Made for your next attempt.', 9, MUTED).pack(anchor='w')
        self.label(rail_bottom, 'WINDOWS  /  x64', 9, PURPLE).pack(anchor='w', pady=(10, 0))

        main = tk.Frame(self, bg=BG, padx=34, pady=26)
        main.pack(side='left', fill='both', expand=True)
        hero = tk.Frame(main, bg=BG)
        hero.pack(fill='x', pady=(0, 14))
        art = tk.Canvas(hero, width=132, height=130, bg=BG, highlightthickness=0)
        art.pack(side='right', padx=(8, 0))
        art.create_image(66, 65, image=self.brand_logo)
        self.label(hero, 'LET’S GET YOU SET UP' if not args.uninstall else 'TAKE A BREAK', 9, PURPLE).pack(anchor='w', pady=(3, 10))
        self.label(hero, 'Make time\nyour playground.' if not args.uninstall else 'Leave things\nas you found them.', 28, FG, bold=True).pack(anchor='w')
        self.label(main, 'Native mods. Time controls. Your next attempt, on your terms.'
                   if not args.uninstall else 'Remove Wood while keeping your personal mods and settings.', 10, MUTED).pack(anchor='w', pady=(0, 14))

        card = tk.Frame(main, bg=PANEL, padx=22, pady=16, highlightthickness=1, highlightbackground='#302c40')
        card.pack(fill='x')
        self.label(card, 'Your TUNG installation', 13, FG, bold=True).pack(anchor='w')
        self.label(card, 'Select the folder containing TUNG.exe.', 10, MUTED).pack(anchor='w', pady=(5, 14))
        self.path = tk.StringVar(value=str(args.game_dir or (games[0] if games else '')))
        field = tk.Frame(card, bg=PANEL)
        field.pack(fill='x')
        self.path_entry = ttk.Entry(field, textvariable=self.path)
        self.path_entry.pack(side='left', fill='x', expand=True)
        self.browse_button = ttk.Button(field, text='Browse…', command=self.browse)
        self.browse_button.pack(side='right', padx=(10, 0))

        self.label(card, 'Before continuing', 10, FG, bold=True).pack(anchor='w', pady=(20, 5))
        self.label(card, 'Close TUNG and Wood. Steam can stay open.', 9, MUTED).pack(anchor='w')

        features = tk.Frame(main, bg=BG)
        features.pack(fill='x', pady=(14, 0))
        for title in ('Native mod menu', 'Time Warp', 'Uninstaller included'):
            self.label(features, '•  ' + title, 9, PURPLE).pack(side='left', padx=(0, 20))
        footer = tk.Frame(main, bg=BG)
        footer.pack(side='bottom', fill='x', pady=(12, 0), before=hero)
        actions = tk.Frame(footer, bg=BG)
        actions.pack(side='bottom', fill='x', pady=(16, 0))
        self.stage = self.label(actions, 'READY WHEN YOU ARE', 9, MUTED)
        self.stage.pack(side='left')
        self.button = ttk.Button(actions, text='Remove Wood  →' if args.uninstall else 'Install Wood  →',
                                 style='Accent.TButton', command=self.run)
        self.button.pack(side='right')
        self.status = self.label(footer, 'Choose your installation above to get started.', 10, MUTED)
        self.status.configure(wraplength=640)
        self.status.pack(anchor='w')
        self.progress = ttk.Progressbar(footer, mode='indeterminate', style='Wood.Horizontal.TProgressbar')
        self.protocol('WM_DELETE_WINDOW', self.close)

    @staticmethod
    def label(parent, value, size, color=FG, bold=False):
        return tk.Label(parent, text=value, bg=parent['bg'], fg=color, justify='left', anchor='w',
                        font=('Segoe UI', size, 'bold' if bold else 'normal'))

    def set_step(self, index):
        for i, box in enumerate(self.steps):
            color = '#29213d' if i == index else '#15141e'
            box.configure(bg=color)
            for child in box.winfo_children():
                child.configure(bg=color)

    def set_busy(self, busy):
        self.busy = busy
        for control in ([self.button, self.path_entry, self.browse_button]
                        + getattr(self, 'mod_checks', [])):
            if control is not None:
                control.configure(state='disabled' if busy else 'normal')
        if busy:
            self.progress.pack(fill='x', pady=(12, 0))
            self.progress.start(12)
            self.set_step(1)
            self.stage.configure(text='WORKING…', fg=PURPLE)
        else:
            self.progress.stop()
            self.progress.pack_forget()

    def close(self):
        if not self.busy:
            self.destroy()
