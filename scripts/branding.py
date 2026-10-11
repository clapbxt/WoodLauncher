"""Create a code-native Wood application icon without external artwork."""
from pathlib import Path
import struct
import zlib


def make_icon(path):
    points = [(4,8),(12,8),(16,26),(20,14),(24,26),(28,8),(36,8),(28,34),(21,34),(20,29),(19,34),(12,34)]
    def inside(x, y):
        odd = False
        for a, b in zip(points, points[1:] + points[:1]):
            if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]: odd = not odd
        return odd
    rows = bytearray()
    for y in range(256):
        rows.append(0)
        for x in range(256):
            rows.extend((89,223,193,255) if inside(x/6.4,y/6.4) else (17,27,37,255))
    def chunk(name, data):
        return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
    png = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',256,256,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b'')
    Path(path).write_bytes(struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHII',0,0,0,0,1,32,len(png),22)+png)
