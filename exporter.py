"""Export FEM models to NASTRAN .dat and .obj file formats."""

from pathlib import Path

import numpy as np


class NastranExporter:
    """Export FEM model to NASTRAN .dat file."""

    @staticmethod
    def export(fem, file_path: str | Path) -> str:
        """Export FEM to NASTRAN .dat file. Returns summary string."""
        return fem.generate_NASTRAN_build(str(file_path))


class ObjExporter:
    """Export FEM model to Wavefront .obj file."""

    @staticmethod
    def export(fem, file_path: str | Path) -> str:
        """Export FEM quad elements to .obj file. Returns summary string."""
        import pyvista as pv

        points = [(grid.X1, grid.X2, grid.X3) for grid in fem.GRID_List]
        point_ids = {grid.ID: i for i, grid in enumerate(fem.GRID_List)}

        faces = []
        for quad in fem.CQUAD4_List:
            ids = [
                point_ids.get(quad.G1),
                point_ids.get(quad.G2),
                point_ids.get(quad.G3),
                point_ids.get(quad.G4),
            ]
            if None not in ids:
                faces.append([4, *ids])

        faces_flat = [val for face in faces for val in face]

        mesh = pv.PolyData(np.array(points), faces_flat)
        mesh.save(str(file_path))

        return f"OBJ file exported to '{file_path}' ({len(faces)} faces, {len(points)} vertices)"
