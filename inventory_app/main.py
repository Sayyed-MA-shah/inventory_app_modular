import sys
import os
import importlib

def _import_modules():
    # Try relative (package) import first
    try:
        from . import database  # type: ignore
        from .ui import main_window as main_window_mod  # type: ignore
        return database, main_window_mod
    except Exception:
        pass

    # Fallback: adjust sys.path so imports work when run as a script
    this_dir = os.path.dirname(__file__)                # .../inventory_app
    project_root = os.path.dirname(this_dir)            # .../inventory_app_modular
    # prefer project_root on sys.path so 'inventory_app' package imports work
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if this_dir not in sys.path:
        sys.path.insert(0, this_dir)

    # Try importing as package first
    for pkg_prefix in ("inventory_app.", ""):
        try:
            database = importlib.import_module(f"{pkg_prefix}database")
            main_window_mod = importlib.import_module(f"{pkg_prefix}ui.main_window")
            return database, main_window_mod
        except Exception:
            continue

    raise ImportError("Could not import database and ui.main_window modules (tried relative and script modes)")

database, main_window_mod = _import_modules()

# main_window module may define either MainWindow (older) or InventoryUI (beta). Pick what's available.
MainClass = getattr(main_window_mod, "MainWindow", None) or getattr(main_window_mod, "InventoryUI", None)
if MainClass is None:
    raise ImportError("ui.main_window does not expose MainWindow or InventoryUI class. Check ui/main_window.py")

def main():
    # ensure DB is initialised if the function exists
    try:
        if hasattr(database, "init_db"):
            database.init_db()
    except Exception:
        # non-fatal: continue to allow UI to run in development
        pass

    app = MainClass()
    app.mainloop()

if __name__ == "__main__":
    main()
else:
    # If imported, expose the main class for external use
    __all__ = ["MainClass"]
    # Also expose database module for external use
    __all__.append("database")

