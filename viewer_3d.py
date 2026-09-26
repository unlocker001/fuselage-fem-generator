"""3D viewport widget wrapping PyVista's QtInteractor for interactive FEM visualization."""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt

import pyvista as pv
from pyvistaqt import QtInteractor

from renderer import FEMRenderer


class Viewer3D(QWidget):
    """Central 3D viewport embedding a PyVista plotter with FEM rendering capabilities."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Configure PyVista for dark background
        pv.global_theme.background = "black"
        pv.global_theme.font.color = "white"

        # Create the interactive plotter widget
        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter.interactor)

        # Create the renderer that manages FEM -> PyVista conversion
        self.renderer = FEMRenderer(self.plotter)

        # Initial empty state
        self.plotter.add_text(
            "Click 'Generate' to build the FEM model",
            position="upper_left", font_size=12, color="gray",
        )

    def render_fem(self, fem):
        """Render a FEM model, replacing any previous visualization."""
        self.renderer.render(fem)


    def toggle_wireframe(self) -> bool:
        """Toggle wireframe/solid mode. Returns True if now wireframe."""
        return self.renderer.toggle_wireframe()

    def set_group_visible(self, group_name: str, visible: bool):
        """Toggle visibility of an element group."""
        self.renderer.set_group_visible(group_name, visible)

    def reset_view(self):
        """Reset camera to fit all geometry."""
        self.renderer.reset_camera()

    def set_view(self, direction: str):
        """Set orthographic view direction: 'xy', 'xz', 'yz', 'iso'."""
        self.renderer.set_view(direction)

    def screenshot(self, file_path: str):
        """Save screenshot of current view."""
        self.renderer.screenshot(file_path)

    def close(self):
        """Clean up the plotter on close."""
        self.plotter.close()
        super().close()
