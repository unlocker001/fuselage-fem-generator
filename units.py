"""Unit system management with metric/imperial conversion.

Internal storage always uses imperial (inches, psi, lb/in^3) to match
the original fuselage generator math. Display converts to/from the
user's selected unit system.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class UnitSystem(Enum):
    IMPERIAL = "imperial"
    METRIC = "metric"


# ── Conversion factors: multiply imperial value by factor to get metric ──

# Length: inches -> millimeters
INCH_TO_MM = 25.4
MM_TO_INCH = 1.0 / INCH_TO_MM

# Stress: psi -> MPa
PSI_TO_MPA = 0.00689476
MPA_TO_PSI = 1.0 / PSI_TO_MPA

# Density: lb/in^3 -> g/cm^3
LBIN3_TO_GCM3 = 27.6799
GCM3_TO_LBIN3 = 1.0 / LBIN3_TO_GCM3

# Area: in^2 -> mm^2
IN2_TO_MM2 = INCH_TO_MM ** 2
MM2_TO_IN2 = MM_TO_INCH ** 2


@dataclass
class UnitDef:
    """Definition of a unit dimension with labels and conversion factors."""
    imperial_label: str
    metric_label: str
    to_metric: float      # multiply imperial value to get metric
    to_imperial: float    # multiply metric value to get imperial


# All unit dimensions used in the application
LENGTH = UnitDef("in", "mm", INCH_TO_MM, MM_TO_INCH)
STRESS = UnitDef("psi", "MPa", PSI_TO_MPA, MPA_TO_PSI)
DENSITY = UnitDef("lb/in\u00b3", "g/cm\u00b3", LBIN3_TO_GCM3, GCM3_TO_LBIN3)
AREA = UnitDef("in\u00b2", "mm\u00b2", IN2_TO_MM2, MM2_TO_IN2)
DIMENSIONLESS = UnitDef("", "", 1.0, 1.0)


def convert(value: float, unit_def: UnitDef, from_system: UnitSystem, to_system: UnitSystem) -> float:
    """Convert a value between unit systems."""
    if from_system == to_system:
        return value
    if from_system == UnitSystem.IMPERIAL and to_system == UnitSystem.METRIC:
        return value * unit_def.to_metric
    else:
        return value * unit_def.to_imperial


def to_display(value: float, unit_def: UnitDef, system: UnitSystem) -> float:
    """Convert internal imperial value to display value in the given unit system."""
    return convert(value, unit_def, UnitSystem.IMPERIAL, system)


def from_display(value: float, unit_def: UnitDef, system: UnitSystem) -> float:
    """Convert display value in the given unit system to internal imperial value."""
    return convert(value, unit_def, system, UnitSystem.IMPERIAL)


def label(unit_def: UnitDef, system: UnitSystem) -> str:
    """Get the display label for a unit in the given system."""
    if system == UnitSystem.METRIC:
        return unit_def.metric_label
    return unit_def.imperial_label


# ── Parameter metadata: maps parameter names to their unit dimensions ──

PARAM_UNITS = {
    "a": LENGTH,
    "b": LENGTH,
    "T": LENGTH,
    "H": LENGTH,
    "h": LENGTH,
    "cmax": DIMENSIONLESS,
    "stringer_spacing": LENGTH,
    "frame_spacing": LENGTH,
    "bayes_number": DIMENSIONLESS,
    "stringer_number": DIMENSIONLESS,
    "E": STRESS,
    "NU": DIMENSIONLESS,
    "RHO": DENSITY,
    "skin_thickness": LENGTH,
    "stringer_area": AREA,
    "frame_web_thickness": LENGTH,
    "frame_edge_area_inner": AREA,
    "frame_edge_area_outer": AREA,
}


# ── Default ranges per unit system (for spin box limits) ──

def length_range_for(system: UnitSystem) -> tuple[float, float]:
    """Return (min, max) for length parameters in the given unit system."""
    if system == UnitSystem.METRIC:
        return (0.025, 12700.0)   # ~0.001 in to 500 in in mm
    return (0.001, 500.0)


def stress_range_for(system: UnitSystem) -> tuple[float, float]:
    if system == UnitSystem.METRIC:
        return (0.007, 689.5)     # ~1000 psi to 100M psi in MPa
    return (1000.0, 100_000_000.0)


def density_range_for(system: UnitSystem) -> tuple[float, float]:
    if system == UnitSystem.METRIC:
        return (0.028, 27.68)     # ~0.001 to 1.0 lb/in^3 in g/cm^3
    return (0.001, 1.0)
