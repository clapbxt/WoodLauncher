"""Small GUI for creating Wood's single-file .tungmod packages."""
from __future__ import annotations

import os
from pathlib import Path
import re
import struct
import sys
import tempfile
import zlib

MAGIC = b'TUNG-MOD/1\n'
MAX_SOURCE = 1024 * 1024
MAX_ICON = 4 * 1024 * 1024
MAX_DIMENSION = 2048
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


def _field(metadata: dict[str, str], key: str, maximum: int) -> str:
    value = str(metadata.get(key, '')).strip()
    if not value or len(value.encode('utf-8')) > maximum or '\n' in value or '\r' in value:
        raise ValueError(f'{key.replace("_", " ").title()} must be 1-{maximum} UTF-8 bytes on one line.')
    return value


def _png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 45 or not data.startswith(PNG_SIGNATURE):
        raise ValueError('The icon must be a valid PNG file.')

    offset = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = interlace = None
    palette = False
    image_data = bytearray()
    saw_idat = saw_iend = False
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError('The icon PNG has a truncated chunk.')
        chunk_length = int.from_bytes(data[offset:offset + 4], 'big')
        chunk_type = data[offset + 4:offset + 8]
        chunk_end = offset + 12 + chunk_length
        if chunk_end > len(data):
            raise ValueError('The icon PNG has a truncated chunk.')
        chunk_data = data[offset + 8:offset + 8 + chunk_length]
        expected_crc = int.from_bytes(data[offset + 8 + chunk_length:chunk_end], 'big')
        if zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF != expected_crc:
            raise ValueError('The icon PNG has an invalid chunk checksum.')
        if width is None and chunk_type != b'IHDR':
            raise ValueError('The icon PNG must start with an IHDR chunk.')
        if chunk_type == b'IHDR':
            if width is not None or chunk_length != 13:
                raise ValueError('The icon PNG has an invalid IHDR chunk.')
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                '>IIBBBBB', chunk_data)
            if compression != 0 or filtering != 0 or interlace not in (0, 1):
                raise ValueError('The icon PNG uses unsupported encoding settings.')
        elif chunk_type == b'PLTE':
            if saw_idat or chunk_length == 0 or chunk_length > 768 or chunk_length % 3:
                raise ValueError('The icon PNG has an invalid palette.')
            palette = True
        elif chunk_type == b'IDAT':
            if saw_iend:
                raise ValueError('The icon PNG has data after IEND.')
            image_data.extend(chunk_data)
            saw_idat = True
        elif chunk_type == b'IEND':
            if chunk_length != 0 or not saw_idat:
                raise ValueError('The icon PNG has an invalid IEND chunk.')
            saw_iend = True
            offset = chunk_end
            break
        elif chunk_type[0] & 0x20 == 0:
            raise ValueError('The icon PNG contains an unsupported critical chunk.')
        offset = chunk_end

    if width is None or height is None or not (0 < width <= MAX_DIMENSION and 0 < height <= MAX_DIMENSION
            and width * height <= 4 * 1024 * 1024):
        raise ValueError('PNG icons must be at most 2048×2048 and 4 megapixels.')
    valid_depths = {
        0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8},
        4: {8, 16}, 6: {8, 16},
    }
    if color_type not in valid_depths or bit_depth not in valid_depths[color_type]:
        raise ValueError('The icon PNG uses an invalid color type or bit depth.')
    if color_type == 3 and not palette:
        raise ValueError('The indexed icon PNG is missing its color palette.')
    if not saw_idat or not saw_iend or offset != len(data):
        raise ValueError('The icon PNG is incomplete or has trailing data.')

    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    bits_per_pixel = channels * bit_depth
    if interlace == 0:
        passes = [(width, height)]
    else:
        passes = []
        for x_start, y_start, x_step, y_step in (
            (0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
            (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2),
        ):
            pass_width = max(0, (width - x_start + x_step - 1) // x_step)
            pass_height = max(0, (height - y_start + y_step - 1) // y_step)
            if pass_width and pass_height:
                passes.append((pass_width, pass_height))
    expected_size = sum(
        pass_height * (1 + (pass_width * bits_per_pixel + 7) // 8)
        for pass_width, pass_height in passes
    )
    inflater = zlib.decompressobj()
    try:
        decoded = inflater.decompress(bytes(image_data), expected_size + 1)
        if inflater.unconsumed_tail:
            raise ValueError('The icon PNG image data expands beyond its dimensions.')
        decoded += inflater.flush()
    except zlib.error as error:
        raise ValueError('The icon PNG image data is corrupt.') from error
    if len(decoded) != expected_size or not inflater.eof or inflater.unused_data:
        raise ValueError('The icon PNG image data is incomplete or corrupt.')
    offset = 0
    for pass_width, pass_height in passes:
        row_size = (pass_width * bits_per_pixel + 7) // 8
        for _ in range(pass_height):
            if decoded[offset] > 4:
                raise ValueError('The icon PNG uses an invalid row filter.')
            offset += row_size + 1
    return width, height


def create_package(lua_path: str | Path, output_path: str | Path,
                   metadata: dict[str, str], icon_path: str | Path | None = None) -> Path:
    lua_file = Path(lua_path)
    if not str(output_path).strip():
        raise ValueError('Choose an output file for the .tungmod package.')
    output_file = Path(output_path)
    if lua_file.suffix.lower() != '.lua':
        raise ValueError('Choose a .lua source file.')
    source = lua_file.read_bytes()
    if not source or len(source) > MAX_SOURCE:
        raise ValueError('Lua source must be between 1 byte and 1 MiB.')
    source.decode('utf-8')

    values = {
        'id': _field(metadata, 'id', 40).lower(),
        'name': _field(metadata, 'name', 80),
        'version': _field(metadata, 'version', 40),
        'author': _field(metadata, 'author', 60),
        'description': _field(metadata, 'description', 500),
    }
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', values['id']):
        raise ValueError('Mod ID must start with a-z or 0-9 and contain only lowercase letters, digits, _ or -.')

    icon = b''
    if icon_path:
        icon = Path(icon_path).read_bytes()
        if not icon or len(icon) > MAX_ICON:
            raise ValueError('PNG icon must be between 1 byte and 4 MiB.')
        _png_dimensions(icon)

    metadata_bytes = ''.join(f'{key}={value}\n' for key, value in values.items()).encode('utf-8')
    if len(metadata_bytes) > 8192:
        raise ValueError('Mod metadata is too large.')
    output_file = output_file.with_suffix('.tungmod')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    payload = (MAGIC + f'{len(metadata_bytes)}\n{len(source)}\n{len(icon)}\n'.encode('ascii')
               + metadata_bytes + source + icon)
    handle, temporary_name = tempfile.mkstemp(prefix=output_file.name + '.', suffix='.tmp',
                                              dir=output_file.parent)
    try:
        with os.fdopen(handle, 'wb') as target:
            target.write(payload)
        os.replace(temporary_name, output_file)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise
    return output_file


def run_gui() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    class Packager(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title('Wood Mod Packager')
            self.geometry('620x620')
            self.minsize(560, 550)
            assets = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
            self.brand_logo = tk.PhotoImage(file=str(assets / 'WoodLauncherLogo.png'))
            self.brand_small = self.brand_logo.subsample(2)
            self.iconphoto(True, self.brand_logo)
            if (assets / 'wood.ico').exists():
                self.iconbitmap(str(assets / 'wood.ico'))
            self.lua_path = tk.StringVar()
            self.icon_path = tk.StringVar()
            self.output_path = tk.StringVar()
            self.fields = {
                key: tk.StringVar(value=default) for key, default in {
                    'id': '', 'name': '', 'version': '1.0.0', 'author': '', 'description': '',
                }.items()
            }
            self._build(ttk)

        def _build(self, ttk):
            frame = ttk.Frame(self, padding=20)
            frame.pack(fill='both', expand=True)
            header = ttk.Frame(frame)
            header.pack(fill='x')
            ttk.Label(header, image=self.brand_small).pack(side='left', padx=(0, 12))
            ttk.Label(header, text='Create a TUNG mod package', font=('Segoe UI', 18, 'bold')).pack(side='left')
            ttk.Label(frame, text='Bundle Lua source, optional PNG artwork, and mod metadata into one .tungmod file.',
                      wraplength=560).pack(anchor='w', pady=(5, 16))
            fields = ttk.Frame(frame)
            fields.pack(fill='x')
            for row, (key, variable) in enumerate(self.fields.items()):
                ttk.Label(fields, text=key.replace('_', ' ').title()).grid(row=row, column=0, sticky='w', pady=5)
                ttk.Entry(fields, textvariable=variable).grid(row=row, column=1, sticky='ew', padx=(12, 0), pady=5)
            fields.columnconfigure(1, weight=1)
            self._path_row(ttk, frame, 'Lua source', self.lua_path, self._choose_lua)
            self._path_row(ttk, frame, 'PNG icon (optional)', self.icon_path, self._choose_icon)
            self._path_row(ttk, frame, 'Output file', self.output_path, self._choose_output)
            ttk.Label(frame, text='Recommended logo: 128×128. PNG limit: 2048×2048, 4 megapixels, 4 MiB. Lua limit: 1 MiB.',
                      wraplength=560).pack(anchor='w', pady=(10, 16))
            ttk.Button(frame, text='Build .tungmod', command=self._package).pack(anchor='e')

        def _path_row(self, ttk, parent, label, variable, callback):
            row = ttk.Frame(parent)
            row.pack(fill='x', pady=5)
            ttk.Label(row, text=label, width=19).pack(side='left')
            ttk.Entry(row, textvariable=variable).pack(side='left', fill='x', expand=True, padx=8)
            ttk.Button(row, text='Browse…', command=callback).pack(side='right')

        def _choose_lua(self):
            path = filedialog.askopenfilename(filetypes=[('Lua source', '*.lua')])
            if path:
                self.lua_path.set(path)
                source = Path(path).stem
                slug = re.sub(r'[^a-z0-9_-]+', '-', source.lower()).strip('-')
                if not self.fields['id'].get():
                    self.fields['id'].set(slug[:40])
                if not self.fields['name'].get():
                    self.fields['name'].set(source)
                output = Path(path).with_suffix('.tungmod')
                self.output_path.set(str(output))

        def _choose_icon(self):
            path = filedialog.askopenfilename(filetypes=[('PNG image', '*.png')])
            if path:
                self.icon_path.set(path)

        def _choose_output(self):
            path = filedialog.asksaveasfilename(defaultextension='.tungmod',
                filetypes=[('Wood mod package', '*.tungmod')])
            if path:
                self.output_path.set(path)

        def _package(self):
            try:
                result = create_package(self.lua_path.get(), self.output_path.get(),
                    {key: value.get() for key, value in self.fields.items()},
                    self.icon_path.get() or None)
            except (OSError, UnicodeError, ValueError) as error:
                messagebox.showerror('Could not build mod package', str(error), parent=self)
                return
            messagebox.showinfo('Mod package created', f'Created:\n{result}\n\nCopy it into TUNG’s Mods folder, then restart the game.', parent=self)

    Packager().mainloop()


if __name__ == '__main__':
    run_gui()
