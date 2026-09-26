"""PyVista-based FEM visualization renderer.

Converts FEM objects into PyVista meshes for interactive 3D display.
Replaces the original Mayavi-based visualization from Classes_Nastran.py.
"""

import math

import numpy as np
import pyvista as pv

# Color map: PID -> (r, g, b) matching original Mayavi colors
ELEMENT_COLORS = {
    # Skin
    11: (0.0, 1.0, 1.0),       # Cyan
    # Stringers
    21: (1.0, 1.0, 0.0),       # Yellow
    # Frame web
    31: (0.4, 0.4, 0.4),       # Gray
    # Frame edge inner
    32: (0.0, 0.8, 0.0),       # Green
    # Frame edge outer
    33: (0.2, 1.0, 0.2),       # Light green
    # Floor longitudinal
    41: (0.5, 0.35, 0.15),     # Brown
    # Floor transverse
    42: (0.5, 0.35, 0.15),     # Brown
    # Floor edges
    43: (0.0, 0.4, 0.4),       # Teal
    44: (0.0, 0.4, 0.4),
    45: (0.0, 0.8, 0.8),       # Light cyan
    46: (0.0, 0.8, 0.8),
    # Floor post
    47: (0.0, 0.8, 0.8),
}

ELEMENT_LABELS = {
    11: "Skin",
    21: "Stringers",
    31: "Frames",
    32: "Frame Edges (inner)",
    33: "Frame Edges (outer)",
    41: "Floor Panels",
    42: "Floor Transverse",
    43: "Floor Edges",
    44: "Floor Edges",
    45: "Floor Trans Edges",
    46: "Floor Trans Edges",
    47: "Floor Posts",
}

# Grouped visibility categories
VISIBILITY_GROUPS = {
    "Skin": [11],
    "Stringers": [21],
    "Frames": [31, 32, 33],
    "Floor": [41, 42, 43, 44, 45, 46, 47],
    "Grid Points": ["points"],
    "Axes": ["axes"],
}

class FEMRenderer:
    """Renders FEM model using PyVista, managing actors for visibility toggling."""

    def __init__(self, plotter):
        self.plotter = plotter
        self.actors = {}          # key -> VTK actor
        self.group_keys = {}      # group_name -> list of actor keys
        self._wireframe = False

    def render(self, fem):
        """Render entire FEM model, replacing any previous visualization."""
        self._fem = fem
        self.plotter.clear()
        self.actors.clear()
        self.group_keys.clear()

        self._render_shells(fem)
        self._render_rods(fem)
        self._render_points(fem)
        self._render_axes(fem)
        self._render_legend(fem)
        self._build_group_keys()
        self.plotter.reset_camera()

    def _render_shells(self, fem):
        """Render CQUAD4 shell elements grouped by PSHELL property."""
        for pshell in fem.PSHELL_List:
            quads = [c for c in fem.CQUAD4_List if c.PID == pshell.PID]
            if not quads:
                continue

            grid_ids = set()
            for q in quads:
                grid_ids.update([q.G1, q.G2, q.G3, q.G4])
            grid_ids = sorted(grid_ids)
            id_to_idx = {gid: i for i, gid in enumerate(grid_ids)}

            points = []
            for gid in grid_ids:
                g = fem.get_object("GRID", gid)
                if g:
                    points.append([g.X1, g.X2, g.X3])
                else:
                    points.append([0, 0, 0])

            faces = []
            for q in quads:
                if all(gid in id_to_idx for gid in [q.G1, q.G2, q.G3, q.G4]):
                    faces.extend([4, id_to_idx[q.G1], id_to_idx[q.G2],
                                  id_to_idx[q.G3], id_to_idx[q.G4]])

            if not points or not faces:
                continue

            mesh = pv.PolyData(np.array(points, dtype=float), faces=faces)
            color = ELEMENT_COLORS.get(pshell.PID, (0.5, 0.5, 0.5))
            label = ELEMENT_LABELS.get(pshell.PID, f"Shell PID={pshell.PID}")

            actor = self.plotter.add_mesh(
                mesh, color=color, show_edges=True,
                edge_color=(0.3, 0.3, 0.3), opacity=0.8,
                label=label, pickable=True,
            )
            key = f"shell_{pshell.PID}"
            self.actors[key] = actor

    def _render_rods(self, fem):
        """Render CROD rod elements grouped by PROD property."""
        for prod in fem.PROD_List:
            rods = [r for r in fem.CROD_List if r.PID == prod.PID]
            if not rods:
                continue

            points = []
            lines = []
            for rod in rods:
                g1 = fem.get_object("GRID", rod.G1)
                g2 = fem.get_object("GRID", rod.G2)
                if g1 and g2:
                    idx = len(points)
                    points.append([g1.X1, g1.X2, g1.X3])
                    points.append([g2.X1, g2.X2, g2.X3])
                    lines.extend([2, idx, idx + 1])

            if not points:
                continue

            mesh = pv.PolyData(np.array(points, dtype=float), lines=lines)
            color = ELEMENT_COLORS.get(prod.PID, (1.0, 1.0, 0.0))
            label = ELEMENT_LABELS.get(prod.PID, f"Rod PID={prod.PID}")

            actor = self.plotter.add_mesh(
                mesh, color=color, line_width=2, label=label, pickable=True,
            )
            key = f"rod_{prod.PID}"
            self.actors[key] = actor

    def _render_points(self, fem):
        """Render grid points as a point cloud (initially hidden)."""
        if not fem.GRID_List:
            return

        points = np.array([[g.X1, g.X2, g.X3] for g in fem.GRID_List], dtype=float)
        cloud = pv.PolyData(points)
        actor = self.plotter.add_mesh(
            cloud, color=(1, 1, 0), point_size=3,
            render_points_as_spheres=True, label="Grid Points",
        )
        actor.SetVisibility(False)  # Hidden by default
        self.actors["points"] = actor

    def _render_axes(self, fem):
        """Render reference coordinate axes."""
        if not fem.GRID_List:
            return

        points = [[g.X1, g.X2, g.X3] for g in fem.GRID_List]
        coords = np.array(points, dtype=float)
        max_val = np.max(np.abs(coords)) if len(coords) > 0 else 10
        axis_len = 1.5 * max_val

        # X axis (red)
        x_line = pv.Line([0, 0, 0], [axis_len, 0, 0])
        ax = self.plotter.add_mesh(x_line, color=(1, 0, 0), line_width=3, label="X Axis")
        self.actors["axis_x"] = ax

        # Y axis (green)
        y_line = pv.Line([0, 0, 0], [0, axis_len, 0])
        ay = self.plotter.add_mesh(y_line, color=(0, 1, 0), line_width=3, label="Y Axis")
        self.actors["axis_y"] = ay

        # Z axis (blue)
        z_line = pv.Line([0, 0, 0], [0, 0, axis_len])
        az = self.plotter.add_mesh(z_line, color=(0, 0, 1), line_width=3, label="Z Axis")
        self.actors["axis_z"] = az

    def _render_legend(self, fem):
        """Add a color legend overlay showing element group colors."""
        # Collect which PIDs are actually present in the model
        present_pids = set()
        for q in fem.CQUAD4_List:
            present_pids.add(q.PID)
        for r in fem.CROD_List:
            present_pids.add(r.PID)

        # Build legend entries: deduplicate by label
        seen = set()
        legend_entries = []
        for pid in sorted(present_pids):
            lbl = ELEMENT_LABELS.get(pid)
            color = ELEMENT_COLORS.get(pid)
            if lbl and color and lbl not in seen:
                seen.add(lbl)
                legend_entries.append([lbl, [int(c * 255) for c in color]])

        if legend_entries:
            self.plotter.add_legend(
                legend_entries,
                bcolor=(0.1, 0.1, 0.1),
                face="rectangle",
                size=(0.15, 0.3),
            )

    def _build_group_keys(self):
        """Map visibility group names to their actor keys."""
        for group_name, pids in VISIBILITY_GROUPS.items():
            keys = []
            for pid in pids:
                if isinstance(pid, str):
                    if pid in self.actors:
                        keys.append(pid)
                    elif pid == "axes":
                        keys.extend(k for k in self.actors if k.startswith("axis_"))
                else:
                    for prefix in ("shell_", "rod_"):
                        key = f"{prefix}{pid}"
                        if key in self.actors:
                            keys.append(key)
            self.group_keys[group_name] = keys

    def set_group_visible(self, group_name: str, visible: bool):
        """Toggle visibility of an element group."""
        keys = self.group_keys.get(group_name, [])
        for key in keys:
            actor = self.actors.get(key)
            if actor:
                actor.SetVisibility(visible)
        self.plotter.render()

    def toggle_wireframe(self):
        """Toggle between wireframe and surface rendering for shell elements."""
        self._wireframe = not self._wireframe
        for key, actor in self.actors.items():
            if key.startswith("shell_"):
                prop = actor.GetProperty()
                if self._wireframe:
                    prop.SetRepresentationToWireframe()
                else:
                    prop.SetRepresentationToSurface()
        self.plotter.render()
        return self._wireframe

    def reset_camera(self):
        """Reset camera to fit all visible geometry."""
        self.plotter.reset_camera()

    def set_view(self, direction: str):
        """Set camera to orthographic view. direction: 'xy', 'xz', 'yz', 'iso'."""
        if direction == "xy":
            self.plotter.view_xy()
        elif direction == "xz":
            self.plotter.view_xz()
        elif direction == "yz":
            self.plotter.view_yz()
        else:
            self.plotter.view_isometric()
        self.plotter.reset_camera()

    def screenshot(self, file_path: str):
        """Save current view as image."""
        self.plotter.screenshot(file_path)
