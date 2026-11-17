"""Load the shared application icon independently of the working directory."""
import logging
from pathlib import Path
from core.resources import resource_path

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication

ICON_PATH = resource_path('resources', 'icons', 'cp2k_studio.png')
logger = logging.getLogger(__name__)


def load_application_icon(path: str | Path | None = None) -> QIcon:
    """Decode after QApplication is created; failures leave Qt's default icon."""
    icon_path = ICON_PATH if path is None else Path(path)
    try:
        if not icon_path.is_file():
            logger.warning('Application icon is missing: %s', icon_path)
            return QIcon()
        pixmap = QPixmap()
        if not pixmap.load(str(icon_path)):
            logger.warning('Application icon could not be decoded: %s', icon_path)
            return QIcon()
        return QIcon(pixmap)
    except (OSError, ValueError, RuntimeError) as exc:
        logger.warning('Application icon could not be loaded: %s (%s)', icon_path, exc)
        return QIcon()


def set_application_icon(app: QApplication) -> QIcon:
    """One application default is inherited by applicable child windows/dialogs."""
    import sys
    if sys.platform == 'win32':
        # Stable taskbar identity, independent of the Python host's icon.
        try:
            import ctypes
            from core.app_info import BUNDLE_IDENTIFIER
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(BUNDLE_IDENTIFIER)
        except (AttributeError, OSError):
            logger.warning('Windows taskbar application identity could not be set')
    icon = load_application_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    return icon
