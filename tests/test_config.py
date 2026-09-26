"""Tests for FuselageConfig dataclass serialization and validation."""

import json
import tempfile
from pathlib import Path

from config import FuselageConfig, MaterialConfig, SectionConfig


class TestFuselageConfig:
    def test_default_values(self):
        cfg = FuselageConfig()
        assert cfg.a == 46.0
        assert cfg.b == 46.0
        assert cfg.T == 0.04
        assert cfg.cmax == 4
        assert cfg.stringer_number == 54

    def test_custom_values(self):
        cfg = FuselageConfig(a=92, b=92, cmax=6)
        assert cfg.a == 92
        assert cfg.b == 92
        assert cfg.cmax == 6

    def test_save_and_load_roundtrip(self, tmp_path):
        original = FuselageConfig(a=100, b=80, T=0.05, cmax=5)
        path = tmp_path / "test_preset.json"
        original.save(path)

        loaded = FuselageConfig.load(path)
        assert loaded.a == original.a
        assert loaded.b == original.b
        assert loaded.T == original.T
        assert loaded.cmax == original.cmax
        assert loaded.stringer_material.E == original.stringer_material.E

    def test_save_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "sub" / "dir" / "preset.json"
        cfg = FuselageConfig()
        cfg.save(path)
        assert path.exists()

    def test_validate_valid_config(self):
        cfg = FuselageConfig()
        assert cfg.validate() is None

    def test_validate_negative_a(self):
        cfg = FuselageConfig(a=-1)
        assert cfg.validate() is not None
        assert "positive" in cfg.validate().lower()

    def test_validate_thickness_too_large(self):
        cfg = FuselageConfig(a=10, b=10, T=15)
        assert cfg.validate() is not None
        assert "thickness" in cfg.validate().lower()

    def test_validate_odd_stringer_count(self):
        cfg = FuselageConfig(stringer_number=55)
        assert cfg.validate() is not None
        assert "even" in cfg.validate().lower()

    def test_validate_cmax_too_low(self):
        cfg = FuselageConfig(cmax=1)
        assert cfg.validate() is not None
        assert "crown" in cfg.validate().lower()

    def test_validate_stringer_limit(self):
        cfg = FuselageConfig(stringer_number=500)
        assert cfg.validate() is not None
        assert "nomenclature" in cfg.validate().lower()

    def test_material_config_defaults(self):
        mat = MaterialConfig()
        assert mat.E == 10_300_000
        assert mat.NU == 0.32
        assert mat.RHO == 0.101
        assert mat.G is None

    def test_section_config_defaults(self):
        sec = SectionConfig()
        assert sec.skin_thickness == 0.04
        assert sec.stringer_area == 0.162
