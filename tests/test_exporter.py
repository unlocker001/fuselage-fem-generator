"""Tests for NASTRAN .dat export functionality."""

from config import FuselageConfig
from fuselage_generator import Fuselage
from exporter import NastranExporter


class TestNastranExporter:
    def test_export_creates_file(self, tmp_path):
        config = FuselageConfig(a=46, b=46, T=0.04, H=50, h=3, cmax=4)
        fus = Fuselage(config=config)
        fem = fus.build_FEM()

        path = tmp_path / "export_test.dat"
        result = NastranExporter.export(fem, path)

        assert path.exists()
        assert "successfully" in result

    def test_export_content_structure(self, tmp_path):
        config = FuselageConfig(a=30, b=30, T=0.03, H=35, h=2, cmax=3)
        fus = Fuselage(config=config)
        fem = fus.build_FEM()

        path = tmp_path / "structure_test.dat"
        NastranExporter.export(fem, path)

        content = path.read_text(encoding="utf-8")
        lines = content.split('\n')

        # Verify document begins with header
        assert lines[0].startswith("$$$ ##### BEGINING DOCUMENT")

        # Verify sections appear in correct order
        section_markers = [
            "POINTS", "MPCS", "MATERIALS",
            "SECTION PROPERTIES", "PRODS", "PSHELLS",
            "ELEMENTS", "CRODS", "CQUAD4",
            "FORCES", "BOUNDARY CONDITIONS", "SPCS",
            "END OF DOCUMENT",
        ]
        last_pos = -1
        for marker in section_markers:
            pos = content.find(marker)
            assert pos > last_pos, f"Section '{marker}' not found or out of order"
            last_pos = pos

    def test_export_grid_count_matches(self, tmp_path):
        config = FuselageConfig(a=46, b=46, T=0.04, H=50, h=3, cmax=4)
        fus = Fuselage(config=config)
        fem = fus.build_FEM()

        path = tmp_path / "count_test.dat"
        NastranExporter.export(fem, path)

        content = path.read_text(encoding="utf-8")
        grid_lines = [line for line in content.split('\n') if line.startswith("GRID,")]
        assert len(grid_lines) == len(fem.GRID_List)

    def test_export_crod_count_matches(self, tmp_path):
        config = FuselageConfig(a=46, b=46, T=0.04, H=50, h=3, cmax=4)
        fus = Fuselage(config=config)
        fem = fus.build_FEM()

        path = tmp_path / "crod_count.dat"
        NastranExporter.export(fem, path)

        content = path.read_text(encoding="utf-8")
        crod_lines = [line for line in content.split('\n') if line.startswith("CROD,")]
        assert len(crod_lines) == len(fem.CROD_List)
