"""Optional PyInstaller support for ASE's dynamic XSD reader and symmetry data.

Used only with --additional-hooks-dir scripts/hooks; no packaging at runtime.
"""
from PyInstaller.utils.hooks import collect_data_files

hiddenimports = ['ase.io.xsd']
datas = collect_data_files('ase.spacegroup', includes=['spacegroup.dat'])
