"""Tests for the Fuselage generator - verifies geometry and element counts."""

from config import FuselageConfig
from fuselage_generator import Fuselage


class TestFuselageDefaults:
    """Test with default (narrow body) parameters matching original script."""

    def setup_method(self):
        # Match the original script: Fuselage(46, 46, 0.04, 46*2-3*12+6, 3, nomenclature, cmax=4)
        self.config = FuselageConfig(a=46, b=46, T=0.04, H=46 * 2 - 3 * 12 + 6, h=3, cmax=4)
        self.fuselage = Fuselage(config=self.config)

    def test_geometry(self):
        assert self.fuselage.a == 46
        assert self.fuselage.b == 46
        assert self.fuselage.Stringer_number == 54
        assert self.fuselage.Bayes_number == 11

    def test_fuselage_length(self):
        expected_L = 15 * 11  # frame_spacing * bayes_number
        assert self.fuselage.L == expected_L

    def test_build_skin_p_count(self):
        skin_pts = self.fuselage.build_skin_p()
        # 12 frames (1 to Bayes+1) * 54 stringers = 648
        assert len(skin_pts) == (11 + 1) * 54

    def test_build_frames_p_count(self):
        frame_pts = self.fuselage.build_frames_p()
        assert len(frame_pts) == (11 + 1) * 54

    def test_build_stringers_count(self):
        stringers = self.fuselage.build_stringers()
        # 11 bays * 54 stringers = 594
        assert len(stringers) == 11 * 54

    def test_build_skin_count(self):
        skin = self.fuselage.build_skin()
        assert len(skin) == 11 * 54

    def test_build_frames_count(self):
        frames = self.fuselage.build_frames()
        assert len(frames) == 12 * 54

    def test_build_fem_returns_fem(self):
        fem = self.fuselage.build_FEM()
        assert fem is not None
        assert len(fem.GRID_List) > 0
        assert len(fem.CROD_List) > 0
        assert len(fem.CQUAD4_List) > 0
        assert len(fem.MAT_List) == 3

    def test_build_fem_has_floor(self):
        """With cmax=4 and valid Hr, floor should be built."""
        fem = self.fuselage.build_FEM()
        # Floor adds PSHELL 41, 42 and PROD 43-47
        pshell_pids = {p.PID for p in fem.PSHELL_List}
        assert 41 in pshell_pids or 42 in pshell_pids

    def test_build_fem_node_uniqueness(self):
        """All grid IDs should be unique (no duplicates from nomenclature)."""
        fem = self.fuselage.build_FEM()
        ids = [g.ID for g in fem.GRID_List]
        assert len(ids) == len(set(ids)), f"Duplicate grid IDs found: {len(ids)} total, {len(set(ids))} unique"

    def test_progress_callback(self):
        progress_calls = []
        fem = self.fuselage.build_FEM(progress_callback=lambda p, m: progress_calls.append((p, m)))
        assert len(progress_calls) > 0
        assert progress_calls[-1][0] == 100


class TestFuselageNoFloor:
    """Test with cmax=2 which should not build a floor."""

    def test_no_floor_with_cmax2(self):
        config = FuselageConfig(a=46, b=46, T=0.04, H=50, h=3, cmax=2)
        fus = Fuselage(config=config)
        fem = fus.build_FEM()
        pshell_pids = {p.PID for p in fem.PSHELL_List}
        # Floor PShells 41, 42 should NOT be present
        assert 41 not in pshell_pids
        assert 42 not in pshell_pids


class TestFuselageElliptical:
    """Test with different a and b (elliptical cross-section)."""

    def test_elliptical_builds(self):
        config = FuselageConfig(a=60, b=40, T=0.04, H=50, h=3, cmax=4)
        fus = Fuselage(config=config)
        fem = fus.build_FEM()
        assert len(fem.GRID_List) > 0
        assert len(fem.CQUAD4_List) > 0


class TestFuselageExport:
    """Test .dat file export produces valid content."""

    def test_dat_export(self, tmp_path):
        config = FuselageConfig(a=46, b=46, T=0.04, H=50, h=3, cmax=4)
        fus = Fuselage(config=config)
        fem = fus.build_FEM()

        dat_path = tmp_path / "test_fuselage.dat"
        result = fem.generate_NASTRAN_build(str(dat_path))

        assert dat_path.exists()
        content = dat_path.read_text(encoding="utf-8")

        # Verify key NASTRAN sections exist
        assert "GRID," in content
        assert "CROD," in content
        assert "CQUAD4," in content
        assert "MAT1," in content
        assert "PROD," in content
        assert "PSHELL," in content
        assert "END OF DOCUMENT" in content

        # Verify node count is reported correctly
        assert str(len(fem.GRID_List)) in result
