"""Background worker for FEM generation using QThread."""

from PySide6.QtCore import QThread, Signal

from config import FuselageConfig
from fuselage_generator import Fuselage


class GenerationWorker(QThread):
    """Runs FEM generation off the main thread to keep UI responsive."""

    progress = Signal(int, str)   # (percent, message)
    finished = Signal(object)     # emits the FEM object
    error = Signal(str)           # emits error message

    def __init__(self, config: FuselageConfig, parent=None):
        super().__init__(parent)
        self.config = config

    def run(self):
        try:
            fuselage = Fuselage(config=self.config)

            # Forward warnings
            for w in fuselage.warnings:
                self.progress.emit(0, f"Warning: {w}")

            fem = fuselage.build_FEM(progress_callback=self._on_progress)
            self.finished.emit(fem)
        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, percent: int, message: str):
        self.progress.emit(percent, message)
