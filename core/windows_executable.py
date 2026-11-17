"""Small read-only PE header inspection; never execute foreign binaries."""
import struct


def pe_info(path):
    with open(path, 'rb') as handle:
        if handle.read(2) != b'MZ':
            raise ValueError('Not a Windows PE executable')
        handle.seek(60)
        offset = struct.unpack('<I', handle.read(4))[0]
        if offset > 16 * 1024 * 1024:
            raise ValueError('Invalid PE header offset')
        handle.seek(offset)
        if handle.read(4) != b'PE\0\0':
            raise ValueError('Invalid PE signature')
        machine = struct.unpack('<H', handle.read(2))[0]
        handle.seek(offset + 24)
        magic = struct.unpack('<H', handle.read(2))[0]
        handle.seek(offset + 24 + 68)
        subsystem = struct.unpack('<H', handle.read(2))[0]
    return machine, magic, subsystem


def is_native_windows_program(path):
    try:
        machine, magic, _ = pe_info(path)
        return machine in {0x8664, 0x14c, 0xaa64} and magic in {0x10b, 0x20b}
    except (OSError, ValueError, struct.error):
        return False
