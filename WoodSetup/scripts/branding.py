"""Use the shared Wood logo for Windows application icons."""
from pathlib import Path
import struct

LOGO = Path(__file__).resolve().parents[1] / 'WoodLauncherLogo.png'


def make_icon(path):
    # ICO supports PNG frames directly; preserve the original artwork and alpha.
    png = LOGO.read_bytes()
    if not png.startswith(b'\x89PNG\r\n\x1a\n') or png[12:16] != b'IHDR':
        raise ValueError('WoodLauncherLogo.png must be a PNG image.')
    width, height = struct.unpack('>II', png[16:24])
    if (width, height) != (128, 128):
        raise ValueError('The shared Wood logo must be 128 by 128 pixels.')
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(struct.pack('<HHH', 0, 1, 1)
                       + struct.pack('<BBBBHHII', width, height, 0, 0, 1, 32, len(png), 22)
                       + png)
