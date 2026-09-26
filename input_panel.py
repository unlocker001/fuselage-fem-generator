"""Left-side input panel with parameter groups, unit system toggle, and live estimators."""

from pathlib import Path

import numpy as np
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QDoubleSpinBox, QSpinBox, QComboBox, QPushButton,
    QScrollArea, QFileDialog, QMessageBox, QFrame, QCheckBox,
)

from config import FuselageConfig, MaterialConfig
from units import (
    UnitSystem, UnitDef, LENGTH, STRESS, DENSITY, AREA, DIMENSIONLESS,
    to_display, from_display, label as unit_label,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


class CollapsibleGroup(QGroupBox):
    """A QGroupBox that can be collapsed/expanded by clicking its title."""

    def __init__(self, title: str, parent=None, collapsed=False):
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setChecked(not collapsed)
        self.toggled.connect(self._on_toggled)

    def _on_toggled(self, checked):
        if not self.layout():
            return
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            w = item.widget()
            if w:
                w.setVisible(checked)
            elif item.layout():
                for j in range(item.layout().count()):
                    sw = item.layout().itemAt(j).widget()
                    if sw:
                        sw.setVisible(checked)


class UnitSpinBox(QDoubleSpinBox):
    """A QDoubleSpinBox aware of its unit dimension for automatic conversion."""

    def __init__(self, unit_def: UnitDef, imperial_value: float,
                 imperial_min: float, imperial_max: float,
                 decimals: int = 4, step: float = 0.01, tooltip: str = "",
                 parent=None):
        super().__init__(parent)
        self.unit_def = unit_def
        self._system = UnitSystem.IMPERIAL
        self._imperial_min = imperial_min
        self._imperial_max = imperial_max
        self._imperial_decimals = decimals
        self._imperial_step = step

        self.setRange(imperial_min, imperial_max)
        self.setDecimals(decimals)
        self.setSingleStep(step)
        self.setValue(imperial_value)
        self._update_suffix()
        if tooltip:
            self.setToolTip(tooltip)
        self.setMinimumWidth(110)

    def _update_suffix(self):
        lbl = unit_label(self.unit_def, self._system)
        self.setSuffix(f" {lbl}" if lbl else "")

    def switch_unit_system(self, new_system: UnitSystem):
        """Convert displayed value and ranges to new unit system."""
        if new_system == self._system:
            return
        # Read current value in imperial
        imperial_val = self.imperial_value()
        self._system = new_system
        # Convert ranges
        new_min = to_display(self._imperial_min, self.unit_def, new_system)
        new_max = to_display(self._imperial_max, self.unit_def, new_system)
        new_val = to_display(imperial_val, self.unit_def, new_system)
        new_step = to_display(self._imperial_step, self.unit_def, new_system)

        # Adjust decimals for metric (mm needs fewer decimals than inches)
        if new_system == UnitSystem.METRIC and self.unit_def is LENGTH:
            self.setDecimals(max(1, self._imperial_decimals - 1))
        elif new_system == UnitSystem.METRIC and self.unit_def is STRESS:
            self.setDecimals(2)
        elif new_system == UnitSystem.METRIC and self.unit_def is DENSITY:
            self.setDecimals(4)
        else:
            self.setDecimals(self._imperial_decimals)

        self.blockSignals(True)
        self.setRange(min(new_min, new_max), max(new_min, new_max))
        self.setSingleStep(abs(new_step))
        self.setValue(new_val)
        self._update_suffix()
        self.blockSignals(False)

    def imperial_value(self) -> float:
        """Get the value in imperial (inches/psi/lb-in3) regardless of display system."""
        return from_display(self.value(), self.unit_def, self._system)

    def set_imperial_value(self, value: float):
        """Set value from imperial, converting to current display system."""
        display_val = to_display(value, self.unit_def, self._system)
        self.setValue(display_val)


def _add_row(layout, label_text, widget):
    row = QHBoxLayout()
    lbl = QLabel(label_text)
    lbl.setMinimumWidth(130)
    row.addWidget(lbl)
    row.addWidget(widget)
    layout.addLayout(row)
    return widget


# ── Cross-Section Preview ─────────────────────────────────────────────────────


class CrossSectionPreview(QWidget):
    """Mini 2D ellipse preview showing cross-section dimensions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(160)
        self.setMinimumWidth(200)
        self.a = 46.0
        self.b = 46.0
        self.T = 0.04
        self._system = UnitSystem.IMPERIAL

    def set_params(self, a: float, b: float, T: float, system: UnitSystem):
        self.a = a
        self.b = b
        self.T = T
        self._system = system
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        # Scale to fit with padding
        max_dim = max(self.a, self.b)
        if max_dim <= 0:
            return
        scale = min(w - 40, h - 40) / (2 * max_dim)

        # Draw outer ellipse (skin)
        pen = QPen(QColor(0, 220, 220), 2)
        painter.setPen(pen)
        painter.setBrush(QColor(0, 60, 60, 80))
        rx_outer = int(self.a * scale)
        ry_outer = int(self.b * scale)
        painter.drawEllipse(cx - rx_outer, cy - ry_outer, 2 * rx_outer, 2 * ry_outer)

        # Draw inner ellipse (frame offset)
        pen2 = QPen(QColor(100, 100, 100), 1, Qt.DashLine)
        painter.setPen(pen2)
        painter.setBrush(Qt.NoBrush)
        offset = min(3, self.a * 0.05)  # Simplified frame offset
        rx_inner = int((self.a - offset) * scale)
        ry_inner = int((self.b - offset) * scale)
        if rx_inner > 0 and ry_inner > 0:
            painter.drawEllipse(cx - rx_inner, cy - ry_inner, 2 * rx_inner, 2 * ry_inner)

        # Draw dimension lines
        pen3 = QPen(QColor(255, 200, 80), 1)
        painter.setPen(pen3)
        # Horizontal (a)
        painter.drawLine(cx - rx_outer, cy, cx + rx_outer, cy)
        # Vertical (b)
        painter.drawLine(cx, cy - ry_outer, cx, cy + ry_outer)

        # Labels
        u = unit_label(LENGTH, self._system)
        a_disp = to_display(self.a, LENGTH, self._system)
        b_disp = to_display(self.b, LENGTH, self._system)
        font = QFont("Segoe UI", 8)
        painter.setFont(font)
        painter.setPen(QColor(220, 220, 220))
        painter.drawText(cx + rx_outer + 4, cy + 4, f"a={a_disp:.1f} {u}")
        painter.drawText(cx + 4, cy - ry_outer - 4, f"b={b_disp:.1f} {u}")

        # Cross-section type label
        ratio = self.a / self.b if self.b > 0 else 1
        if abs(ratio - 1.0) < 0.01:
            shape_text = "Circular"
        else:
            shape_text = f"Elliptical (a/b={ratio:.2f})"
        painter.drawText(5, 14, shape_text)

        painter.end()


# ── Computed Properties Display ───────────────────────────────────────────────


class PropertiesDisplay(QFrame):
    """Shows computed geometric properties (perimeter, area, fineness, etc.)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        self.lbl_perimeter = QLabel("Perimeter: --")
        self.lbl_area = QLabel("Cross-section area: --")
        self.lbl_length = QLabel("Fuselage length: --")
        self.lbl_fineness = QLabel("Fineness ratio: --")
        self.lbl_floor_width = QLabel("Floor width: --")
        self.lbl_est_nodes = QLabel("Est. nodes: --")
        self.lbl_est_elements = QLabel("Est. elements: --")

        for lbl in [self.lbl_perimeter, self.lbl_area, self.lbl_length,
                     self.lbl_fineness, self.lbl_floor_width,
                     self.lbl_est_nodes, self.lbl_est_elements]:
            lbl.setStyleSheet("font-size: 11px; color: #bbbbbb;")
            layout.addWidget(lbl)

    def update_from_config(self, config: FuselageConfig, system: UnitSystem):
        """Compute and display properties from current config."""
        a, b = config.a, config.b
        P = np.pi * np.sqrt(2 * (a ** 2 + b ** 2))
        A = np.pi * a * b
        R = 2 * A / P if P > 0 else 1
        L = config.frame_spacing * config.bayes_number
        fineness = 0.5 * L / R if R > 0 else 0

        u = unit_label(LENGTH, system)
        u2 = unit_label(AREA, system)

        P_d = to_display(P, LENGTH, system)
        A_d = to_display(A, AREA, system)
        L_d = to_display(L, LENGTH, system)

        self.lbl_perimeter.setText(f"Perimeter: {P_d:,.1f} {u}")
        self.lbl_area.setText(f"Cross-section area: {A_d:,.1f} {u2}")
        self.lbl_length.setText(f"Fuselage length: {L_d:,.1f} {u}")
        self.lbl_fineness.setText(f"Fineness ratio: {fineness:.2f}")

        # Floor width estimate
        try:
            sn = config.stringer_number
            i1_list = [config.H - (b - config.T) * (1 - np.sin(2 * (i - 1) * np.pi / sn + np.pi / 2))
                       for i in range(1, sn // 2 + 1)]
            i1 = np.argmin(np.abs(i1_list)) + 1
            fw = abs(2 * a * np.cos(2 * (i1 - 1) * np.pi / sn + np.pi / 2))
            fw_d = to_display(fw, LENGTH, system)
            self.lbl_floor_width.setText(f"Floor width: {fw_d:,.1f} {u}")
        except Exception:
            self.lbl_floor_width.setText("Floor width: N/A")

        # Element count estimate
        n_frames = config.bayes_number + 1
        n_str = config.stringer_number
        cmax = config.cmax

        est_grid = 1 + (n_frames * n_str * 2)  # skin + frames
        est_crod = config.bayes_number * n_str  # stringers
        est_crod += n_frames * n_str * 2  # frame edges
        est_cquad = config.bayes_number * n_str  # skin
        est_cquad += n_frames * n_str  # frames

        if cmax > 2:
            floor_pts = n_frames * (cmax - 2) * 4
            est_grid += floor_pts
            est_crod += n_frames * 6 + config.bayes_number * (cmax - 2) * 8  # rough floor edges
            est_cquad += n_frames * (cmax - 1) + config.bayes_number * (cmax - 2) * 4  # rough floor panels

        self.lbl_est_nodes.setText(f"Est. nodes: ~{est_grid:,}")
        self.lbl_est_elements.setText(f"Est. elements: ~{est_crod + est_cquad:,}")


# ── Main Input Panel ──────────────────────────────────────────────────────────


class InputPanel(QDockWidget):
    """Dockable input panel with parameters, unit toggle, preview, and live estimator."""

    config_changed = Signal()
    unit_system_changed = Signal(object)  # Emits UnitSystem

    def __init__(self, parent=None):
        super().__init__("Parameters", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setMinimumWidth(340)
        self._unit_system = UnitSystem.IMPERIAL

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setAlignment(Qt.AlignTop)

        # ---- Unit System Toggle ----
        unit_group = QGroupBox("Unit System")
        unit_layout = QHBoxLayout(unit_group)
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["Imperial (in, psi, lb/in\u00b3)", "Metric (mm, MPa, g/cm\u00b3)"])
        self.unit_combo.currentIndexChanged.connect(self._on_unit_changed)
        unit_layout.addWidget(self.unit_combo)
        main_layout.addWidget(unit_group)

        # ---- Cross-Section Preview ----
        self.preview = CrossSectionPreview()
        main_layout.addWidget(self.preview)

        # ---- Cross-Section Group ----
        geo_group = QGroupBox("Cross-Section Geometry")
        geo_layout = QVBoxLayout(geo_group)
        self.spin_a = _add_row(geo_layout, "Semi-major a:", UnitSpinBox(
            LENGTH, 46.0, 1.0, 500.0, 2, 1.0, "Semi-major axis of elliptical cross-section"))
        self.spin_b = _add_row(geo_layout, "Semi-minor b:", UnitSpinBox(
            LENGTH, 46.0, 1.0, 500.0, 2, 1.0, "Semi-minor axis (equals a for circular)"))
        self.spin_T = _add_row(geo_layout, "Skin thickness T:", UnitSpinBox(
            LENGTH, 0.04, 0.001, 5.0, 4, 0.005, "Fuselage skin panel thickness"))
        main_layout.addWidget(geo_group)

        # ---- Floor Group ----
        floor_group = QGroupBox("Floor Parameters")
        floor_layout = QVBoxLayout(floor_group)
        self.spin_H = _add_row(floor_layout, "Ref height H:", UnitSpinBox(
            LENGTH, 50.0, 0.1, 500.0, 2, 1.0, "Vertical reference height for floor positioning"))
        self.spin_h = _add_row(floor_layout, "Floor depth h:", UnitSpinBox(
            LENGTH, 3.0, 0.0, 50.0, 2, 0.5, "Depth of the floor beam structure"))
        self.spin_cmax = QSpinBox()
        self.spin_cmax.setRange(2, 20)
        self.spin_cmax.setValue(4)
        self.spin_cmax.setToolTip("Number of crown divisions (higher = finer floor mesh)")
        self.spin_cmax.setMinimumWidth(110)
        _add_row(floor_layout, "Crown count:", self.spin_cmax)
        main_layout.addWidget(floor_group)

        # ---- Structure Group (collapsed) ----
        struct_group = CollapsibleGroup("Structural Layout", collapsed=True)
        struct_layout = QVBoxLayout(struct_group)
        self.spin_stringer_spacing = _add_row(struct_layout, "Stringer spacing:", UnitSpinBox(
            LENGTH, 6.0, 1.0, 24.0, 2, 0.5, "Circumferential spacing between stringers"))
        self.spin_frame_spacing = _add_row(struct_layout, "Frame spacing:", UnitSpinBox(
            LENGTH, 15.0, 5.0, 60.0, 2, 1.0, "Longitudinal spacing between frames"))
        self.spin_bayes = QSpinBox()
        self.spin_bayes.setRange(1, 100)
        self.spin_bayes.setValue(11)
        self.spin_bayes.setToolTip("Number of bays along fuselage length")
        self.spin_bayes.setMinimumWidth(110)
        _add_row(struct_layout, "Bay count:", self.spin_bayes)
        self.spin_stringers = QSpinBox()
        self.spin_stringers.setRange(4, 498)
        self.spin_stringers.setSingleStep(2)
        self.spin_stringers.setValue(54)
        self.spin_stringers.setToolTip("Number of circumferential stringers (must be even)")
        self.spin_stringers.setMinimumWidth(110)
        _add_row(struct_layout, "Stringer count:", self.spin_stringers)
        main_layout.addWidget(struct_group)

        # ---- Materials Group (collapsed) ----
        mat_group = CollapsibleGroup("Material Properties", collapsed=True)
        mat_layout = QVBoxLayout(mat_group)
        mat_layout.addWidget(QLabel("Stringer / Skin / Frame (identical by default)"))
        self.spin_E = _add_row(mat_layout, "Young's Modulus E:", UnitSpinBox(
            STRESS, 10_300_000, 1000, 100_000_000, 0, 100000, "Elastic modulus"))
        self.spin_NU = _add_row(mat_layout, "Poisson's Ratio:", UnitSpinBox(
            DIMENSIONLESS, 0.32, 0.0, 0.5, 4, 0.01, "Poisson's ratio"))
        self.spin_RHO = _add_row(mat_layout, "Density:", UnitSpinBox(
            DENSITY, 0.101, 0.001, 1.0, 4, 0.001, "Material density"))
        main_layout.addWidget(mat_group)

        # ---- Loads & Pressurization ----
        loads_group = QGroupBox("Loads & Pressurization")
        loads_layout = QVBoxLayout(loads_group)
        self.spin_pressure = _add_row(loads_layout, "Cabin pressure:", UnitSpinBox(
            STRESS, 9.7, 0.0, 30.0, 2, 0.1, "Operating cabin differential pressure (GAG cycle)"))
        self.spin_dsg = QSpinBox()
        self.spin_dsg.setRange(1000, 500_000)
        self.spin_dsg.setSingleStep(500)
        self.spin_dsg.setValue(15_000)
        self.spin_dsg.setMinimumWidth(110)
        self.spin_dsg.setToolTip("Design service goal: target life in flight cycles")
        _add_row(loads_layout, "Service goal (flights):", self.spin_dsg)
        main_layout.addWidget(loads_group)

        # ---- Windows (controllable cutouts) ----
        win_group = CollapsibleGroup("Windows (Cutouts)", collapsed=True)
        win_layout = QVBoxLayout(win_group)
        self.chk_windows = QCheckBox("Enable windows")
        self.chk_windows.setChecked(True)
        self.chk_windows.setToolTip("Model cabin windows as stress-concentration cutouts")
        win_layout.addWidget(self.chk_windows)
        self.spin_win_circ_start = QSpinBox()
        self.spin_win_circ_start.setRange(1, 498)
        self.spin_win_circ_start.setValue(9)
        self.spin_win_circ_start.setMinimumWidth(110)
        self.spin_win_circ_start.setToolTip("First stringer index of the window band (mirrored on the far side)")
        _add_row(win_layout, "Band start stringer:", self.spin_win_circ_start)
        self.spin_win_circ_width = QSpinBox()
        self.spin_win_circ_width.setRange(1, 20)
        self.spin_win_circ_width.setValue(3)
        self.spin_win_circ_width.setMinimumWidth(110)
        self.spin_win_circ_width.setToolTip("Stringers spanned by each window band")
        _add_row(win_layout, "Band width:", self.spin_win_circ_width)
        self.spin_win_bay_start = QSpinBox()
        self.spin_win_bay_start.setRange(1, 100)
        self.spin_win_bay_start.setValue(3)
        self.spin_win_bay_start.setMinimumWidth(110)
        self.spin_win_bay_start.setToolTip("First bay carrying a window")
        _add_row(win_layout, "First bay:", self.spin_win_bay_start)
        self.spin_win_bay_step = QSpinBox()
        self.spin_win_bay_step.setRange(1, 20)
        self.spin_win_bay_step.setValue(2)
        self.spin_win_bay_step.setMinimumWidth(110)
        self.spin_win_bay_step.setToolTip("Bays between windows (2 = one intact bay between openings)")
        _add_row(win_layout, "Bay step:", self.spin_win_bay_step)
        self.spin_win_semi = _add_row(win_layout, "Window half-height:", UnitSpinBox(
            LENGTH, 4.5, 0.5, 30.0, 2, 0.5, "Window half-height transverse to the hoop stress"))
        self.spin_win_radius = _add_row(win_layout, "Corner radius:", UnitSpinBox(
            LENGTH, 1.0, 0.1, 10.0, 2, 0.1, "Window corner radius (sharper = higher stress concentration)"))
        self.spin_win_reinf = _add_row(win_layout, "Reinforcement:", UnitSpinBox(
            DIMENSIONLESS, 0.75, 0.1, 1.0, 2, 0.05, "Reinforcement efficiency (1 = unreinforced cutout)"))
        main_layout.addWidget(win_group)

        # ---- Computed Properties ----
        props_group = QGroupBox("Computed Properties")
        props_layout = QVBoxLayout(props_group)
        self.properties_display = PropertiesDisplay()
        props_layout.addWidget(self.properties_display)
        main_layout.addWidget(props_group)

        # ---- Presets Group ----
        preset_group = QGroupBox("Presets")
        preset_layout = QVBoxLayout(preset_group)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Custom", "Narrow Body (737)", "Wide Body (777)", "Regional Jet"])
        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        preset_layout.addWidget(self.preset_combo)

        btn_row = QHBoxLayout()
        self.btn_save_preset = QPushButton("Save Preset...")
        self.btn_save_preset.clicked.connect(self._on_save_preset)
        btn_row.addWidget(self.btn_save_preset)
        self.btn_load_preset = QPushButton("Load Preset...")
        self.btn_load_preset.clicked.connect(self._on_load_preset)
        btn_row.addWidget(self.btn_load_preset)
        preset_layout.addLayout(btn_row)
        main_layout.addWidget(preset_group)

        main_layout.addStretch()
        scroll.setWidget(container)
        self.setWidget(scroll)

        # Connect all spinboxes to config_changed + live update
        for spin in self._unit_spins():
            spin.valueChanged.connect(self._on_any_value_changed)
        for spin in self._int_spins():
            spin.valueChanged.connect(self._on_any_value_changed)
        self.chk_windows.toggled.connect(self._on_any_value_changed)

        # Initial computed properties
        self._update_live_displays()

    def _unit_spins(self) -> list[UnitSpinBox]:
        return [self.spin_a, self.spin_b, self.spin_T, self.spin_H, self.spin_h,
                self.spin_stringer_spacing, self.spin_frame_spacing,
                self.spin_E, self.spin_NU, self.spin_RHO,
                self.spin_pressure, self.spin_win_semi, self.spin_win_radius,
                self.spin_win_reinf]

    def _int_spins(self) -> list[QSpinBox]:
        return [self.spin_cmax, self.spin_bayes, self.spin_stringers,
                self.spin_dsg, self.spin_win_circ_start, self.spin_win_circ_width,
                self.spin_win_bay_start, self.spin_win_bay_step]

    def _on_any_value_changed(self):
        self._update_live_displays()
        self.config_changed.emit()

    def _update_live_displays(self):
        """Update cross-section preview and computed properties from current values."""
        config = self.get_config()
        self.preview.set_params(config.a, config.b, config.T, self._unit_system)
        self.properties_display.update_from_config(config, self._unit_system)

    # ---- Unit System ----

    @property
    def unit_system(self) -> UnitSystem:
        return self._unit_system

    def _on_unit_changed(self, index):
        new_system = UnitSystem.METRIC if index == 1 else UnitSystem.IMPERIAL
        if new_system == self._unit_system:
            return
        self._unit_system = new_system
        for spin in self._unit_spins():
            spin.switch_unit_system(new_system)
        self._update_live_displays()
        self.unit_system_changed.emit(new_system)

    # ---- Config I/O ----

    def get_config(self) -> FuselageConfig:
        """Build FuselageConfig from current UI values (always in imperial internally)."""
        mat = MaterialConfig(
            E=self.spin_E.imperial_value(),
            NU=self.spin_NU.imperial_value(),
            RHO=self.spin_RHO.imperial_value(),
        )
        return FuselageConfig(
            a=self.spin_a.imperial_value(),
            b=self.spin_b.imperial_value(),
            T=self.spin_T.imperial_value(),
            H=self.spin_H.imperial_value(),
            h=self.spin_h.imperial_value(),
            cmax=self.spin_cmax.value(),
            stringer_spacing=self.spin_stringer_spacing.imperial_value(),
            frame_spacing=self.spin_frame_spacing.imperial_value(),
            bayes_number=self.spin_bayes.value(),
            stringer_number=self.spin_stringers.value(),
            stringer_material=mat,
            skin_material=MaterialConfig(E=mat.E, NU=mat.NU, RHO=mat.RHO),
            frame_material=MaterialConfig(E=mat.E, NU=mat.NU, RHO=mat.RHO),
            # Loads / pressurization
            operating_pressure=self.spin_pressure.imperial_value(),
            design_service_goal=self.spin_dsg.value(),
            # Damage tolerance
            # Windows
            windows_enabled=self.chk_windows.isChecked(),
            window_bay_start=self.spin_win_bay_start.value(),
            window_bay_step=self.spin_win_bay_step.value(),
            window_circ_start=self.spin_win_circ_start.value(),
            window_circ_width=self.spin_win_circ_width.value(),
            window_semi_axis=self.spin_win_semi.imperial_value(),
            window_corner_radius=self.spin_win_radius.imperial_value(),
            window_reinforcement=self.spin_win_reinf.imperial_value(),
        )

    def set_config(self, config: FuselageConfig):
        """Update all UI widgets from a FuselageConfig (values in imperial)."""
        # Block all signals during batch update
        all_widgets = self._unit_spins() + self._int_spins()
        for w in all_widgets:
            w.blockSignals(True)
        self.chk_windows.blockSignals(True)
        try:
            self.spin_a.set_imperial_value(config.a)
            self.spin_b.set_imperial_value(config.b)
            self.spin_T.set_imperial_value(config.T)
            self.spin_H.set_imperial_value(config.H)
            self.spin_h.set_imperial_value(config.h)
            self.spin_cmax.setValue(config.cmax)
            self.spin_stringer_spacing.set_imperial_value(config.stringer_spacing)
            self.spin_frame_spacing.set_imperial_value(config.frame_spacing)
            self.spin_bayes.setValue(config.bayes_number)
            self.spin_stringers.setValue(config.stringer_number)
            self.spin_E.set_imperial_value(config.stringer_material.E)
            self.spin_NU.set_imperial_value(config.stringer_material.NU)
            self.spin_RHO.set_imperial_value(config.stringer_material.RHO)
            # Loads / pressurization
            self.spin_pressure.set_imperial_value(config.operating_pressure)
            self.spin_dsg.setValue(int(config.design_service_goal))
            # Damage tolerance
            # Windows
            self.chk_windows.setChecked(bool(config.windows_enabled))
            self.spin_win_bay_start.setValue(int(config.window_bay_start))
            self.spin_win_bay_step.setValue(int(config.window_bay_step))
            self.spin_win_circ_start.setValue(int(config.window_circ_start))
            self.spin_win_circ_width.setValue(int(config.window_circ_width))
            self.spin_win_semi.set_imperial_value(config.window_semi_axis)
            self.spin_win_radius.set_imperial_value(config.window_corner_radius)
            self.spin_win_reinf.set_imperial_value(config.window_reinforcement)
        finally:
            for w in all_widgets:
                w.blockSignals(False)
            self.chk_windows.blockSignals(False)
        self._update_live_displays()

    # ---- Presets ----

    _BUILTIN_PRESETS = {
        "Narrow Body (737)": FuselageConfig(a=46, b=46, T=0.04, H=50, h=3, cmax=4,
                                            bayes_number=11, stringer_number=54),
        "Wide Body (777)": FuselageConfig(a=92, b=92, T=0.06, H=100, h=4, cmax=6,
                                          bayes_number=20, stringer_number=108),
        "Regional Jet": FuselageConfig(a=30, b=30, T=0.03, H=35, h=2, cmax=3,
                                       bayes_number=8, stringer_number=36),
    }

    def _on_preset_selected(self, name):
        if name in self._BUILTIN_PRESETS:
            self.set_config(self._BUILTIN_PRESETS[name])
            self.config_changed.emit()

    def _on_save_preset(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Preset", "", "JSON Files (*.json)")
        if path:
            config = self.get_config()
            config.save(path)
            QMessageBox.information(self, "Preset Saved", f"Preset saved to:\n{path}")

    def _on_load_preset(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Preset", "", "JSON Files (*.json)")
        if path:
            try:
                config = FuselageConfig.load(path)
                self.set_config(config)
                self.preset_combo.setCurrentText("Custom")
                self.config_changed.emit()
                QMessageBox.information(self, "Preset Loaded", f"Preset loaded from:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load preset:\n{e}")
