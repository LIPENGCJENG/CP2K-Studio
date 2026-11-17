"""Version-checked CP2K 2026.1 XML interface, shared with cp2k-input-tools."""
from i18n.messages import i18n_msg, i18n_str
from functools import lru_cache
from pathlib import Path
from core.resources import resource_path
import re
import xml.etree.ElementTree as ET

BUNDLED_XML = resource_path('schemas', 'cp2k_input_2026.1.xml')


@lru_cache(maxsize=4)
def _read(path: str, signature: tuple):
    root = ET.parse(path).getroot()
    version = root.findtext('CP2K_VERSION', '')
    if not re.search(r'\b2026\.1\b', version):
        raise ValueError(i18n_msg('CP2K 2026.1 XML is required; found {p0}', code='studio.5b9edbd269dba7f4', p0=version or i18n_msg('Unknown version', code='studio.f1e7bec171ae3b9e')))
    return root


class CP2KSchema:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or BUNDLED_XML).expanduser().resolve()
        stat = self.path.stat()
        self.root = _read(i18n_str(self.path), (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size, stat.st_ino))

    @property
    def version(self):
        return self.root.findtext('CP2K_VERSION')

    def section(self, path: str):
        node = self.root
        for name in path.strip('/').split('/'):
            if name.upper() in {'CP2K_INPUT', ''}:
                continue
            node = next((s for s in node.findall('SECTION')
                         if name.upper() in [n.text for n in s.findall('NAME')]), None)
            if node is None:
                raise KeyError(path)
        return node

    def keywords(self, path: str):
        return [k.findtext('NAME') for k in self.section(path).findall('KEYWORD')]

    def keyword(self, path: str, name: str):
        for item in self.section(path).findall('KEYWORD'):
            if name.upper() in [n.text for n in item.findall('NAME')]:
                return {'name': item.findtext('NAME'),
                        'description': item.findtext('DESCRIPTION', ''),
                        'default': item.findtext('DEFAULT_VALUE'),
                        'type': item.find('DATA_TYPE').attrib if item.find('DATA_TYPE') is not None else {},
                        'enum': [v.text for v in item.findall('.//ENUMERATION/ITEM/NAME')]}
        raise KeyError(f'{path}/{name}')
