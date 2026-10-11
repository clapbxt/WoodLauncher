from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from lupa.lua54 import LuaRuntime
from WoodModPackager import create_package


def png_fixture(width=32, height=32):
    def chunk(name, data):
        return (struct.pack('>I', len(data)) + name + data
                + struct.pack('>I', zlib.crc32(name + data) & 0xFFFFFFFF))

    header = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    pixels = b''.join(b'\x00' + b'\x00' * (width * 4) for _ in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header)
            + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b''))


class ModPackagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wood-mod-package-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lua_file = self.root / 'helper.lua'
        self.lua_file.write_text("return {description='Lua description'}\n", encoding='utf-8')
        self.icon_file = self.root / 'helper.png'
        self.icon_file.write_bytes(png_fixture())
        self.metadata = {
            'id': 'helper-mod',
            'name': 'Helper Mod',
            'version': '1.2.0',
            'author': 'Wood',
            'description': 'A helpful mod.',
        }

    def test_package_round_trips_metadata_lua_and_png_through_runtime_reader(self):
        package_file = create_package(self.lua_file, self.root / 'out', self.metadata, self.icon_file)
        self.assertEqual(package_file.suffix, '.tungmod')
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().package_path = str(package_file).replace('\\', '/')
        lua.globals().icon_prefix = str(self.root / 'icon-').replace('\\', '/')
        reader = Path('NativeMods/WoodRuntime/Scripts/mod_package.lua').read_text(encoding='utf-8')
        lua.globals().reader = lua.execute(reader)
        metadata, source, icon_path = lua.eval('reader.read(package_path, icon_prefix)')
        self.assertEqual(metadata['id'], 'helper-mod')
        self.assertEqual(metadata['name'], 'Helper Mod')
        self.assertEqual(metadata['version'], '1.2.0')
        self.assertEqual(metadata['author'], 'Wood')
        self.assertEqual(metadata['description'], 'A helpful mod.')
        self.assertIn("Lua description", source)
        self.assertEqual(Path(icon_path).read_bytes(), self.icon_file.read_bytes())

    def test_packager_rejects_unsafe_ids_invalid_pngs_and_multiline_metadata(self):
        with self.assertRaisesRegex(ValueError, 'Mod ID'):
            create_package(self.lua_file, self.root / 'bad', {**self.metadata, 'id': '../bad'})
        self.icon_file.write_bytes(b'not a png')
        with self.assertRaisesRegex(ValueError, 'valid PNG'):
            create_package(self.lua_file, self.root / 'bad', self.metadata, self.icon_file)
        with self.assertRaisesRegex(ValueError, 'one line'):
            create_package(self.lua_file, self.root / 'bad', {**self.metadata, 'name': 'Bad\nname'})

    def test_packager_rejects_corrupt_png_chunks(self):
        self.icon_file.write_bytes(png_fixture()[:-5] + b'\x00\x00\x00\x00\x00')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            create_package(self.lua_file, self.root / 'bad', self.metadata, self.icon_file)

    def test_png_icon_is_optional(self):
        package_file = create_package(self.lua_file, self.root / 'without-icon', self.metadata)
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().package_path = str(package_file).replace('\\', '/')
        lua.globals().icon_prefix = str(self.root / 'icon-').replace('\\', '/')
        lua.globals().reader = lua.execute(
            Path('NativeMods/WoodRuntime/Scripts/mod_package.lua').read_text(encoding='utf-8'))
        metadata, source, icon_path = lua.eval('reader.read(package_path, icon_prefix)')
        self.assertEqual(metadata['id'], 'helper-mod')
        self.assertIn('Lua description', source)
        self.assertIsNone(icon_path)

    def test_runtime_rejects_truncated_package(self):
        package_file = self.root / 'broken.tungmod'
        package_file.write_bytes(b'TUNG-MOD/1\n30\n25\n128\n')
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().package_path = str(package_file).replace('\\', '/')
        lua.globals().icon_prefix = str(self.root / 'icon-').replace('\\', '/')
        lua.globals().reader = lua.execute(
            Path('NativeMods/WoodRuntime/Scripts/mod_package.lua').read_text(encoding='utf-8'))
        with self.assertRaises(Exception):
            lua.eval('reader.read(package_path, icon_prefix)')


if __name__ == '__main__':
    unittest.main()
