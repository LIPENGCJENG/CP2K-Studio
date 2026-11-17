"""Console-only bundled helper. Never import Qt or create an application."""
from core.local_run_runtime import main

if __name__ == '__main__':
    raise SystemExit(main())
