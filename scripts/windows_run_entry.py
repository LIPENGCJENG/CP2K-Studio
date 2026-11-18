"""Console-only Windows helper; never import QApplication."""
from core.windows_run_runtime import main

if __name__ == '__main__':
    raise SystemExit(main())
