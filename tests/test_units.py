"""Tests for unit conversion system."""

import math

from units import (
    UnitSystem, UnitDef, LENGTH, STRESS, DENSITY, AREA, DIMENSIONLESS,
    INCH_TO_MM, PSI_TO_MPA, LBIN3_TO_GCM3, IN2_TO_MM2,
    convert, to_display, from_display, label, PARAM_UNITS,
    length_range_for, stress_range_for, density_range_for,
)


class TestConversionFactors:
    def test_inch_to_mm(self):
        assert INCH_TO_MM == 25.4

    def test_psi_to_mpa(self):
        assert abs(PSI_TO_MPA - 0.00689476) < 1e-8

    def test_in2_to_mm2(self):
        assert abs(IN2_TO_MM2 - 25.4 ** 2) < 1e-6


class TestConvert:
    def test_same_system_noop(self):
        assert convert(10.0, LENGTH, UnitSystem.IMPERIAL, UnitSystem.IMPERIAL) == 10.0

    def test_imperial_to_metric_length(self):
        result = convert(1.0, LENGTH, UnitSystem.IMPERIAL, UnitSystem.METRIC)
        assert abs(result - 25.4) < 1e-6

    def test_metric_to_imperial_length(self):
        result = convert(25.4, LENGTH, UnitSystem.METRIC, UnitSystem.IMPERIAL)
        assert abs(result - 1.0) < 1e-6

    def test_imperial_to_metric_stress(self):
        result = convert(1000.0, STRESS, UnitSystem.IMPERIAL, UnitSystem.METRIC)
        assert abs(result - 1000 * PSI_TO_MPA) < 1e-6

    def test_imperial_to_metric_density(self):
        result = convert(0.1, DENSITY, UnitSystem.IMPERIAL, UnitSystem.METRIC)
        assert abs(result - 0.1 * LBIN3_TO_GCM3) < 1e-4

    def test_imperial_to_metric_area(self):
        result = convert(1.0, AREA, UnitSystem.IMPERIAL, UnitSystem.METRIC)
        assert abs(result - IN2_TO_MM2) < 1e-6

    def test_dimensionless_noop(self):
        result = convert(42.0, DIMENSIONLESS, UnitSystem.IMPERIAL, UnitSystem.METRIC)
        assert result == 42.0

    def test_roundtrip(self):
        """Convert imperial->metric->imperial should return original value."""
        original = 46.0
        metric = convert(original, LENGTH, UnitSystem.IMPERIAL, UnitSystem.METRIC)
        back = convert(metric, LENGTH, UnitSystem.METRIC, UnitSystem.IMPERIAL)
        assert abs(back - original) < 1e-10


class TestToDisplay:
    def test_imperial_passthrough(self):
        assert to_display(10.0, LENGTH, UnitSystem.IMPERIAL) == 10.0

    def test_metric_converts(self):
        result = to_display(1.0, LENGTH, UnitSystem.METRIC)
        assert abs(result - 25.4) < 1e-6


class TestFromDisplay:
    def test_imperial_passthrough(self):
        assert from_display(10.0, LENGTH, UnitSystem.IMPERIAL) == 10.0

    def test_metric_converts_back(self):
        result = from_display(25.4, LENGTH, UnitSystem.METRIC)
        assert abs(result - 1.0) < 1e-6


class TestLabel:
    def test_imperial_length(self):
        assert label(LENGTH, UnitSystem.IMPERIAL) == "in"

    def test_metric_length(self):
        assert label(LENGTH, UnitSystem.METRIC) == "mm"

    def test_imperial_stress(self):
        assert label(STRESS, UnitSystem.IMPERIAL) == "psi"

    def test_metric_stress(self):
        assert label(STRESS, UnitSystem.METRIC) == "MPa"

    def test_dimensionless_empty(self):
        assert label(DIMENSIONLESS, UnitSystem.IMPERIAL) == ""
        assert label(DIMENSIONLESS, UnitSystem.METRIC) == ""


class TestParamUnits:
    def test_a_is_length(self):
        assert PARAM_UNITS["a"] is LENGTH

    def test_E_is_stress(self):
        assert PARAM_UNITS["E"] is STRESS

    def test_RHO_is_density(self):
        assert PARAM_UNITS["RHO"] is DENSITY

    def test_stringer_area_is_area(self):
        assert PARAM_UNITS["stringer_area"] is AREA

    def test_cmax_is_dimensionless(self):
        assert PARAM_UNITS["cmax"] is DIMENSIONLESS


class TestRangeFunctions:
    def test_length_range_imperial(self):
        lo, hi = length_range_for(UnitSystem.IMPERIAL)
        assert lo == 0.001
        assert hi == 500.0

    def test_length_range_metric(self):
        lo, hi = length_range_for(UnitSystem.METRIC)
        assert lo == 0.025
        assert hi == 12700.0

    def test_stress_range_imperial(self):
        lo, hi = stress_range_for(UnitSystem.IMPERIAL)
        assert lo == 1000.0

    def test_density_range_imperial(self):
        lo, hi = density_range_for(UnitSystem.IMPERIAL)
        assert lo == 0.001
        assert hi == 1.0
