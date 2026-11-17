"""CP2K Studio desktop entry point (Python 3.10+)."""
import sys


def main():
    from core.app_info import APP_NAME, APP_VERSION
    if len(sys.argv) == 3 and sys.argv[1] == '--packaging-smoke-test':
        from scripts.macos_smoke import run
        return run(sys.argv[2])
    if getattr(sys, 'frozen', False):
        import logging
        from logging.handlers import RotatingFileHandler
        from core.resources import user_data_directory
        try:
            log = user_data_directory() / 'logs' / 'studio.log'
            log.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(log, maxBytes=1024 * 1024, backupCount=2, encoding='utf-8')
            logging.basicConfig(level=logging.INFO, handlers=[handler],
                                format='%(asctime)s %(levelname)s %(name)s: %(message)s')
            logging.info('Starting %s %s', APP_NAME, APP_VERSION)
        except OSError:
            pass
    try:
        from PySide6.QtWidgets import QApplication
        from ui.main_window import MainWindow
        from ui.app_icon import set_application_icon
    except ImportError as exc:
        print(f"Missing dependency: {exc}\nRun python -m pip install -r requirements.txt", file=sys.stderr)
        return 1
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("CP2K Studio")
    icon = set_application_icon(app)
    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
