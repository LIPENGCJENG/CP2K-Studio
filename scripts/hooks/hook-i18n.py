"""PyInstaller hook: preserve translations beside the imported i18n package.

Enable with --additional-hooks-dir scripts/hooks. PyInstaller is optional and is
not required for source launches. TS is needed for legacy diagnostic spelling;
QM drives the actual Qt interface translations.
"""
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('i18n', includes=['*.ts', '*.qm'])
