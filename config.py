"""Fuselage FEM configuration dataclasses with JSON serialization for presets."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class MaterialConfig:
    """Material properties for a single MAT1 card."""
    E: float = 10_300_000       # Young's modulus (psi)
    NU: float = 0.32            # Poisson's ratio
    RHO: float = 0.101          # Density (lb/in^3)
    G: float | None = None      # Shear modulus (computed from E, NU if None)


@dataclass
class SectionConfig:
    """Cross-section property values for all PROD and PSHELL elements."""
    skin_thickness: float = 0.04
    stringer_area: float = 0.162
    frame_web_thickness: float = 0.055
    frame_edge_area_inner: float = 0.038
    frame_edge_area_outer: float = 0.038
    floor_long_thickness: float = 0.078
    floor_trans_thickness: float = 0.1
    floor_long_edge_top_area: float = 0.197
    floor_long_edge_bot_area: float = 0.033
    floor_trans_edge_top_area: float = 0.050
    floor_trans_edge_bot_area: float = 0.037
    floor_post_area: float = 0.078


@dataclass
class FuselageConfig:
    """Complete fuselage FEM configuration. Serializable to/from JSON for presets."""

    # Primary geometry (user must specify)
    a: float = 46.0             # Semi-major axis (inches)
    b: float = 46.0             # Semi-minor axis (inches)
    T: float = 0.04             # Skin thickness (inches)
    H: float = 50.0             # Reference height (inches)
    h: float = 3.0              # Floor beam depth (inches)
    cmax: int = 4               # Crown count

    # Structural layout
    stringer_spacing: float = 6.0       # Circumferential stringer spacing (inches)
    frame_spacing: float = 15.0         # Longitudinal frame spacing (inches)
    bayes_number: int = 11              # Number of bays
    stringer_number: int = 54           # Number of stringers (must be even)

    # Materials
    stringer_material: MaterialConfig = field(default_factory=MaterialConfig)
    skin_material: MaterialConfig = field(default_factory=MaterialConfig)
    frame_material: MaterialConfig = field(default_factory=MaterialConfig)

    # Section properties
    sections: SectionConfig = field(default_factory=SectionConfig)

    # ---- Loads and pressurization ----
    operating_pressure: float = 9.7     # cabin differential pressure (psi)
    design_service_goal: int = 15000    # target service life (flight cycles)

    # ---- Window placement (controllable cutouts) ----
    windows_enabled: bool = True
    window_bay_start: int = 3           # first bay carrying a window (1-based)
    window_bay_step: int = 2           # bays between consecutive windows (2 = every other)
    window_bay_count: int = 0          # limit number of window bays (0 = all matching)
    window_circ_start: int = 9         # first stringer index of the window band
    window_circ_width: int = 3         # stringers spanned by the window band (per side)
    window_semi_axis: float = 4.5      # window half-height transverse to the hoop (inches)
    window_corner_radius: float = 1.0  # window corner radius (inches)
    window_reinforcement: float = 0.75  # reinforcement efficiency in (0, 1]; 1 = unreinforced

    def save(self, path: Path | str) -> None:
        """Save configuration to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> FuselageConfig:
        """Load configuration from JSON file."""
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        # Reconstruct nested dataclasses
        for mat_key in ("stringer_material", "skin_material", "frame_material"):
            if mat_key in data and isinstance(data[mat_key], dict):
                data[mat_key] = MaterialConfig(**data[mat_key])
        if "sections" in data and isinstance(data["sections"], dict):
            data["sections"] = SectionConfig(**data["sections"])
        return cls(**data)

    def validate(self) -> str | None:
        """Validate configuration. Returns error message or None if valid."""
        if self.a <= 0 or self.b <= 0:
            return "Semi-axes (a, b) must be positive."
        if self.T <= 0:
            return "Skin thickness (T) must be positive."
        if self.T >= min(self.a, self.b):
            return "Skin thickness must be less than the smaller semi-axis."
        if self.stringer_number < 4:
            return "Stringer count must be at least 4."
        if self.stringer_number % 2 != 0:
            return "Stringer count must be even."
        if self.cmax < 2:
            return "Crown count (cmax) must be at least 2."
        if self.H <= 0:
            return "Reference height (H) must be positive."
        if self.h < 0:
            return "Floor beam depth (h) cannot be negative."
        if self.bayes_number < 1:
            return "Bay count must be at least 1."
        if self.frame_spacing <= 0:
            return "Frame spacing must be positive."
        if self.stringer_spacing <= 0:
            return "Stringer spacing must be positive."
        if 2 * self.stringer_number > 999:
            return "Grid numbering exceeds nomenclature limit (stringer_number too high)."
        # ---- Loads ----
        if self.operating_pressure < 0:
            return "Operating pressure cannot be negative."
        if self.design_service_goal <= 0:
            return "Design service goal must be positive."
        # ---- Window placement ----
        if self.windows_enabled:
            if self.window_bay_start < 1:
                return "Window start bay must be at least 1."
            if self.window_bay_step < 1:
                return "Window bay step must be at least 1."
            if self.window_circ_start < 1:
                return "Window stringer start index must be at least 1."
            if self.window_circ_width < 1:
                return "Window band width must span at least one stringer."
            if self.window_circ_start + self.window_circ_width - 1 > self.stringer_number:
                return "Window band exceeds the available stringers."
            if self.window_corner_radius <= 0:
                return "Window corner radius must be positive."
            if not (0 < self.window_reinforcement <= 1):
                return "Window reinforcement efficiency must be in the range (0, 1]."
        return None
