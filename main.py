"""Fuselage FEM Generator - Parametric Aircraft Fuselage FEM Model Generator.

Author: Massinissa Ben Djoudi
Version: 2.0
"""

import sys
from pathlib import Path

# Ensure the application directory is on the Python path
app_dir = str(Path(__file__).parent)
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from main_window import MainWindow


def _selftest() -> int:
    """Headless bundle check: import the stack and build one model, no window.

    Used to verify a frozen (PyInstaller) build has every module and can generate
    a mesh, without needing a display or an OpenGL context.
    """
    from config import FuselageConfig
    from fuselage_generator import Fuselage

    cfg = FuselageConfig()
    fem = Fuselage(config=cfg).build_FEM()
    print(f"SELFTEST OK: {fem.statistics['nodes']} nodes, "
          f"{fem.statistics['total_elements']} elements")
    return 0


def main():
    if "--selftest" in sys.argv:
        sys.exit(_selftest())

    # Enable high-DPI scaling for sharp rendering on modern displays
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Fuselage FEM Generator")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Massinissa Ben Djoudi")

    # Set application icon
    icon_path = Path(__file__).parent / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Apply dark fusion style for a professional engineering look
    app.setStyle("Fusion")
    from PySide6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, QColor(220, 220, 220))
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
    palette.setColor(QPalette.Text, QColor(220, 220, 220))
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, QColor(220, 220, 220))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(128, 128, 128))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(128, 128, 128))
    app.setPalette(palette)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
