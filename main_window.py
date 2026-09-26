"""Main application window for the Fuselage FEM Generator GUI."""

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QKeySequence, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QMenuBar, QToolBar, QStatusBar, QLabel,
    QProgressBar, QFileDialog, QMessageBox, QApplication,
)

from config import FuselageConfig
from input_panel import InputPanel
from viewer_3d import Viewer3D
from generation_worker import GenerationWorker
from exporter import NastranExporter, ObjExporter
from renderer import VISIBILITY_GROUPS
from units import UnitSystem


class MainWindow(QMainWindow):
    """Main application window with toolbar, input panel, 3D viewport, and status bar."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fuselage FEM Generator - by Massinissa Ben Djoudi")
        self.resize(1400, 900)
        self.setMinimumSize(800, 600)

        # Set window icon
        icon_path = Path(__file__).parent / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.fem = None
        self.worker = None
        self._undo_stack = []
        self._redo_stack = []

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_signals()

    def _setup_ui(self):
        """Create the central 3D viewport and left input panel."""
        # Central 3D viewport
        self.viewer = Viewer3D(self)
        self.setCentralWidget(self.viewer)

        # Left input panel (dockable)
        self.input_panel = InputPanel(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.input_panel)

    def _setup_menu(self):
        """Create the application menu bar."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        new_action = file_menu.addAction("&New (Reset)")
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self._on_reset)

        file_menu.addSeparator()

        load_preset = file_menu.addAction("&Open Preset...")
        load_preset.setShortcut(QKeySequence("Ctrl+O"))
        load_preset.triggered.connect(self.input_panel._on_load_preset)

        save_preset = file_menu.addAction("&Save Preset...")
        save_preset.setShortcut(QKeySequence("Ctrl+S"))
        save_preset.triggered.connect(self.input_panel._on_save_preset)

        file_menu.addSeparator()

        export_dat = file_menu.addAction("Export &DAT File...")
        export_dat.setShortcut(QKeySequence("Ctrl+E"))
        export_dat.triggered.connect(self._on_export_dat)

        export_obj = file_menu.addAction("Export &OBJ File...")
        export_obj.triggered.connect(self._on_export_obj)

        export_screenshot = file_menu.addAction("Export Screenshot...")
        export_screenshot.triggered.connect(self._on_screenshot)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut(QKeySequence("Alt+F4"))
        exit_action.triggered.connect(self.close)

        # View menu
        view_menu = menu_bar.addMenu("&View")

        self._visibility_actions = {}
        for group_name in VISIBILITY_GROUPS:
            action = view_menu.addAction(group_name)
            action.setCheckable(True)
            action.setChecked(group_name not in ("Grid Points",))  # Points off by default
            action.toggled.connect(lambda checked, gn=group_name: self.viewer.set_group_visible(gn, checked))
            self._visibility_actions[group_name] = action

        view_menu.addSeparator()

        wireframe_action = view_menu.addAction("Toggle &Wireframe")
        wireframe_action.setShortcut(QKeySequence("W"))
        wireframe_action.triggered.connect(self._on_toggle_wireframe)

        view_menu.addSeparator()

        view_menu.addAction("View &XY").triggered.connect(lambda: self.viewer.set_view("xy"))
        view_menu.addAction("View X&Z").triggered.connect(lambda: self.viewer.set_view("xz"))
        view_menu.addAction("View &YZ").triggered.connect(lambda: self.viewer.set_view("yz"))
        view_menu.addAction("View &Isometric").triggered.connect(lambda: self.viewer.set_view("iso"))

        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        about_action = help_menu.addAction("&About")
        about_action.triggered.connect(self._on_about)

    def _setup_toolbar(self):
        """Create the main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # Generate button
        self.btn_generate = toolbar.addAction("Generate Model")
        self.btn_generate.setShortcut(QKeySequence("Ctrl+G"))
        self.btn_generate.setToolTip("Generate FEM model from current parameters (Ctrl+G)")
        self.btn_generate.triggered.connect(self._on_generate)

        toolbar.addSeparator()

        # Export buttons
        self.btn_export_dat = toolbar.addAction("Export DAT")
        self.btn_export_dat.setToolTip("Export to NASTRAN .dat file (Ctrl+E)")
        self.btn_export_dat.triggered.connect(self._on_export_dat)
        self.btn_export_dat.setEnabled(False)

        self.btn_export_obj = toolbar.addAction("Export OBJ")
        self.btn_export_obj.setToolTip("Export to Wavefront .obj file")
        self.btn_export_obj.triggered.connect(self._on_export_obj)
        self.btn_export_obj.setEnabled(False)

        toolbar.addSeparator()

        # View buttons
        toolbar.addAction("Reset View").triggered.connect(self.viewer.reset_view)

        self.btn_wireframe = toolbar.addAction("Wireframe")
        self.btn_wireframe.setCheckable(True)
        self.btn_wireframe.triggered.connect(self._on_toggle_wireframe)

    def _setup_statusbar(self):
        """Create the status bar with statistics and progress bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.lbl_stats = QLabel("No model loaded")
        self.status_bar.addWidget(self.lbl_stats, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def _connect_signals(self):
        """Wire up signal connections."""
        self.input_panel.unit_system_changed.connect(self._on_unit_system_changed)

    def _on_unit_system_changed(self, system: UnitSystem):
        """Update status bar unit display when unit system changes."""
        name = "Metric" if system == UnitSystem.METRIC else "Imperial"
        if self.fem:
            stats = self.fem.statistics
            self.lbl_stats.setText(
                f"Nodes: {stats['nodes']:,}  |  "
                f"Elements: {stats['total_elements']:,} "
                f"({stats['rod_elements']:,} rods + {stats['quad_elements']:,} quads)  |  "
                f"Units: {name}"
            )
        else:
            self.lbl_stats.setText(f"No model loaded  |  Units: {name}")

    # ---- Actions ----

    def _on_generate(self):
        """Start FEM generation in background thread."""
        config = self.input_panel.get_config()
        error = config.validate()
        if error:
            QMessageBox.warning(self, "Invalid Parameters", error)
            return

        # Save undo state
        self._undo_stack.append(config)
        self._redo_stack.clear()

        # Disable generate button during generation
        self.btn_generate.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_stats.setText("Generating...")

        self.worker = GenerationWorker(config, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_generation_done)
        self.worker.error.connect(self._on_generation_error)
        self.worker.start()

    def _on_progress(self, percent, message):
        self.progress_bar.setValue(percent)
        self.lbl_stats.setText(message)

    def _on_generation_done(self, fem):
        self.fem = fem
        self.viewer.render_fem(fem)

        stats = fem.statistics
        self.lbl_stats.setText(
            f"Nodes: {stats['nodes']:,}  |  "
            f"Elements: {stats['total_elements']:,} "
            f"({stats['rod_elements']:,} rods + {stats['quad_elements']:,} quads)  |  "
            f"Materials: {stats['materials']}  |  "
            f"Properties: {stats['rod_properties'] + stats['shell_properties']}"
        )

        self.progress_bar.setVisible(False)
        self.btn_generate.setEnabled(True)
        self.btn_export_dat.setEnabled(True)
        self.btn_export_obj.setEnabled(True)

    def _on_generation_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.btn_generate.setEnabled(True)
        self.lbl_stats.setText("Generation failed.")
        QMessageBox.critical(self, "Generation Error", f"FEM generation failed:\n\n{error_msg}")

    def _on_export_dat(self):
        if not self.fem:
            QMessageBox.information(self, "No Model", "Generate a model first before exporting.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export NASTRAN File", self.fem.File_address,
            "NASTRAN Files (*.dat);;All Files (*)")
        if path:
            try:
                result = NastranExporter.export(self.fem, path)
                self.lbl_stats.setText(f"Exported: {path}")
                QMessageBox.information(self, "Export Successful", result)
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def _on_export_obj(self):
        if not self.fem:
            QMessageBox.information(self, "No Model", "Generate a model first before exporting.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export OBJ File", "fuselage.obj",
            "OBJ Files (*.obj);;All Files (*)")
        if path:
            try:
                result = ObjExporter.export(self.fem, path)
                self.lbl_stats.setText(f"Exported: {path}")
                QMessageBox.information(self, "Export Successful", result)
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def _on_screenshot(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Screenshot", "fuselage_screenshot.png",
            "PNG Files (*.png);;All Files (*)")
        if path:
            self.viewer.screenshot(path)
            self.lbl_stats.setText(f"Screenshot saved: {path}")

    def _on_toggle_wireframe(self):
        is_wireframe = self.viewer.toggle_wireframe()
        self.btn_wireframe.setChecked(is_wireframe)

    def _on_reset(self):
        """Reset all parameters to defaults."""
        self.input_panel.set_config(FuselageConfig())
        self.input_panel.preset_combo.setCurrentText("Custom")

    def _on_about(self):
        QMessageBox.about(
            self,
            "About Fuselage FEM Generator",
            "<h2>Fuselage FEM Generator</h2>"
            "<p>Version 2.0</p>"
            "<p><b>Author:</b> Massinissa Ben Djoudi</p>"
            "<p>Parametric aircraft fuselage finite element model generator with "
            "interactive 3D visualization.</p>"
            "<p>Generates NASTRAN-compatible .dat files for use in "
            "MSC Patran/Nastran and similar FEA software.</p>"
            "<hr>"
            "<p><b>Modelling:</b></p>"
            "<ul>"
            "<li>Elliptical cross-section with configurable semi-axes</li>"
            "<li>Longitudinal stringers, circumferential frames and floor structure</li>"
            "<li>Controllable window cutouts (placement, size, reinforcement)</li>"
            "<li>Export to .dat (NASTRAN) and .obj (CAD) formats</li>"
            "<li>Metric/Imperial units, presets, cross-section preview</li>"
            "</ul>"
        )

    def closeEvent(self, event):
        """Clean up resources on window close."""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        self.viewer.close()
        event.accept()
