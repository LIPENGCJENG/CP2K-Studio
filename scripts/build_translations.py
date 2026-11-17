"""Extract Message templates with Qt lupdate, then compile distributable QM files.

Usage: python scripts/build_translations.py [--update]
Edit translations in i18n/*.ts (Qt Linguist). Application startup uses shipped
QM files and never requires translation tools or network access.
"""
import argparse
import ast
from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'i18n'


def templates():
    result = {}
    for folder in ['ui', 'core', 'i18n']:
        for path in (ROOT / folder).rglob('*.py'):
            if path.name == 'catalog_sources.py':
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == 'i18n_msg' and node.args and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)):
                    source = node.args[0].value
                    code = next((k.value.value for k in node.keywords if k.arg == 'code' and isinstance(k.value, ast.Constant)), None)
                    code = code or 'studio.' + sha256(source.encode()).hexdigest()[:16]
                    result[(code, source)] = f'{path.relative_to(ROOT)}:{node.lineno}'
    return result


def tool(name):
    local = Path(sys.executable).parent / name
    found = str(local) if local.is_file() else shutil.which(name)
    if not found:
        raise SystemExit(f'{name} was not found. Install requirements.txt using this Python environment.')
    return found


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--update', action='store_true', help='Extract current sources with pyside6-lupdate')
    args = args.parse_args()
    if args.update:
        lines = ['"""Generated Qt extraction markers. Edit Message templates in UI/core sources."""',
                 'from PySide6.QtCore import QCoreApplication', '', 'def catalog_sources():', '    return [']
        for (code, source), location in sorted(templates().items()):
            lines += [f'        # {location}', f'        QCoreApplication.translate("CP2KStudio", {source!r}, {code!r}),']
        lines.append('    ]')
        markers = DIRECTORY / 'catalog_sources.py'
        markers.write_text('\n'.join(lines)+'\n', encoding='utf-8')
        subprocess.run([tool('pyside6-lupdate'), str(markers), '-no-obsolete', '-ts',
                        str(DIRECTORY / 'cp2kstudio_en_US.ts'), str(DIRECTORY / 'cp2kstudio_zh_CN.ts')], check=True)
        # English is the explicit fallback. New untranslated Chinese entries
        # remain unfinished and Qt correctly falls back to that English source.
        en = DIRECTORY / 'cp2kstudio_en_US.ts'
        tree = ET.parse(en)
        for message in tree.findall('.//message'):
            translation = message.find('translation')
            if translation is None:
                translation = ET.SubElement(message, 'translation')
            translation.attrib.pop('type', None)
            translation.text = message.findtext('source')
        ET.indent(tree, '  ')
        tree.write(en, encoding='utf-8', xml_declaration=True)
    for language in ['en_US', 'zh_CN']:
        ts = DIRECTORY / f'cp2kstudio_{language}.ts'
        subprocess.run([tool('pyside6-lrelease'), str(ts), '-qm', str(ts.with_suffix('.qm'))], check=True)


if __name__ == '__main__':
    main()
