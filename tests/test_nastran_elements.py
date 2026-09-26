"""Tests for NASTRAN element card formatting."""

from nastran_elements import MAT1, GRID, PROD, CROD, PSHELL, CQUAD4, FEM


class TestMAT1:
    def test_repr_format(self):
        mat = MAT1(1, 10300000, None, 0.31999999, 0.101, None, None, None, None, None, None, None, 8)
        text = repr(mat)
        assert text.startswith("MAT1,")
        assert "10300000" in text
        assert "0.31999999" in text
        assert "0.101" in text

    def test_mid_in_output(self):
        mat = MAT1(42, 1e7, None, 0.3, 0.1, None, None, None, None, None, None, None, 8)
        assert "42" in repr(mat)


class TestGRID:
    def test_repr_format(self):
        grid = GRID(100, None, 1.5, 2.5, 3.5, None, None, 8)
        text = repr(grid)
        assert text.startswith("GRID,")
        assert "100" in text
        assert "1.5" in text
        assert "2.5" in text
        assert "3.5" in text

    def test_get_point(self):
        grid = GRID(5, None, 10.0, 20.0, 30.0, None, None, 8)
        point = grid.get_point()
        assert point == [5, 10.0, 20.0, 30.0]


class TestPROD:
    def test_repr_format(self):
        prod = PROD(21, 1, 0.162, None, None, None, 8, (1, 1, 0))
        text = repr(prod)
        assert text.startswith("PROD,")
        assert "21" in text
        assert "0.162" in text


class TestCROD:
    def test_repr_format(self):
        crod = CROD(1001, 21, 100, 200, 8)
        text = repr(crod)
        assert text.startswith("CROD,")
        assert "1001" in text
        assert "21" in text
        assert "100" in text
        assert "200" in text


class TestPSHELL:
    def test_repr_format(self):
        pshell = PSHELL(11, 2, 0.04, None, None, None, None, None, None, None, None, 8, (0, 1, 1), (0, 0, 1))
        text = repr(pshell)
        assert text.startswith("PSHELL,")
        assert "11" in text
        assert "0.04" in text


class TestCQUAD4:
    def test_repr_format(self):
        cquad = CQUAD4(5001, 11, 100, 200, 300, 400, None, None, 8)
        text = repr(cquad)
        assert text.startswith("CQUAD4,")
        assert "5001" in text
        assert "100" in text
        assert "200" in text
        assert "300" in text
        assert "400" in text


class TestFEM:
    def _make_simple_fem(self):
        """Create a minimal FEM for testing."""
        grids = [
            GRID(1, None, 0, 0, 0, None, None, 8),
            GRID(2, None, 1, 0, 0, None, None, 8),
            GRID(3, None, 1, 1, 0, None, None, 8),
            GRID(4, None, 0, 1, 0, None, None, 8),
        ]
        mats = [MAT1(1, 1e7, None, 0.3, 0.1, None, None, None, None, None, None, None, 8)]
        prods = [PROD(21, 1, 0.1, None, None, None, 8, (1, 1, 0))]
        pshells = [PSHELL(11, 1, 0.04, None, None, None, None, None, None, None, None, 8, (0, 1, 1), (0, 0, 1))]
        crods = [CROD(1, 21, 1, 2, 8)]
        cquads = [CQUAD4(100, 11, 1, 2, 3, 4, None, None, 8)]
        return FEM("Test", grids, [], mats, prods, pshells, crods, cquads, [], "test_output")

    def test_repr_stats(self):
        fem = self._make_simple_fem()
        text = repr(fem)
        assert "4 nodes" in text
        assert "2 elements" in text

    def test_statistics(self):
        fem = self._make_simple_fem()
        stats = fem.statistics
        assert stats["nodes"] == 4
        assert stats["rod_elements"] == 1
        assert stats["quad_elements"] == 1
        assert stats["total_elements"] == 2
        assert stats["materials"] == 1

    def test_get_object_grid(self):
        fem = self._make_simple_fem()
        g = fem.get_object("GRID", 1)
        assert g is not None
        assert g.X1 == 0

    def test_get_object_missing(self):
        fem = self._make_simple_fem()
        assert fem.get_object("GRID", 999) is None

    def test_generate_nastran_build(self, tmp_path):
        fem = self._make_simple_fem()
        path = str(tmp_path / "test.dat")
        result = fem.generate_NASTRAN_build(path)
        assert "successfully generated" in result

        content = open(path, encoding="utf-8").read()
        assert "BEGINING DOCUMENT" in content
        assert "GRID," in content
        assert "CROD," in content
        assert "CQUAD4," in content
        assert "MAT1," in content
        assert "END OF DOCUMENT" in content
