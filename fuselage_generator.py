"""Parametric fuselage FEM generator.

Refactored from Fuselage_Generator.py:
- Removed unused imports (matplotlib, os, re)
- Parameterized hardcoded constants via FuselageConfig
- Added progress callback for GUI integration
- Removed module-level execution
"""

import numpy as np

from nastran_elements import (
    MAT1, GRID, PROD, CROD, PSHELL, CQUAD4, MPC, SPC1, FEM,
)
from config import FuselageConfig


class Nomenclature:
    def __init__(self, func, MAX_Length):
        self.MAX_Length = MAX_Length
        self.Script_Spacing = -(-self.MAX_Length // 8) * 8
        self.func = func


def fonction_nomenclature(Object, Data):
    if Object == "MPC":
        return int(100 * Data[0] + Data[1])
    if Object == "GRID":
        return int(1e4 * Data[0] + 1e3 * Data[1] + Data[2])
    if Object == "CROD":
        return int(1e6 * Data[0] + 1e4 * Data[1] + 1e3 * Data[2] + Data[3])
    if Object == "CQUAD4":
        return int(1e6 * Data[0] + 1e4 * Data[1] + 1e3 * Data[2] + Data[3])
    return None


class Fuselage:
    """Parametric aircraft fuselage FEM generator with elliptical cross-section."""

    def setup_radiuses(self):
        a, b = self.a, self.b
        P = self.P
        Pr = (P // self.Stringer_spacing) * self.Stringer_spacing
        dP = Pr - P
        if np.abs(dP) >= self.Stringer_spacing / 2:
            Pr += self.Stringer_spacing
            ar = a * Pr / P
            br = (b / a) * ar
            return ar, br
        elif np.abs(dP) < self.Stringer_spacing / 2:
            ar = a * Pr / P
            br = (b / a) * ar
            return ar, br
        else:
            return a, b

    def setup_floor_index(self):
        lst1 = [self.H - (self.br - self.T) * (1 - np.sin(2 * (i - 1) * np.pi / self.Stringer_number + np.pi / 2))
                for i in range(1, self.Stringer_number // 2 + 1)]
        i1 = np.argmin(np.abs(lst1)) + 1
        Hr = (self.br - self.T) * (1 - np.sin(2 * (i1 - 1) * np.pi / self.Stringer_number + np.pi / 2))
        lst2 = [Hr + self.h - (self.br - self.T) * (1 - np.sin(2 * (i - 1) * np.pi / self.Stringer_number + np.pi / 2))
                for i in range(1, self.Stringer_number // 2 + 1)]
        w = abs(2 * self.ar * np.cos(2 * (i1 - 1) * np.pi / self.Stringer_number + np.pi / 2))
        lst3 = [0.5 * w / (self.cmax - 1) + self.ar * np.cos(2 * (i - 1) * np.pi / self.Stringer_number + np.pi / 2)
                for i in range(self.Stringer_number // 4 + 1, self.Stringer_number // 2 + 1)]
        return i1, np.argmin([-x if x < 0 else np.inf for x in lst2]) + 1, np.argmin(np.abs(lst3)) + self.Stringer_number // 4 + 1

    def __init__(self, config: FuselageConfig | None = None, **kwargs):
        """Initialize fuselage generator from FuselageConfig or individual parameters.

        Args:
            config: FuselageConfig instance with all parameters.
            **kwargs: Individual parameters (a, b, T, H, h, cmax, etc.) for backward compatibility.
        """
        if config is None:
            config = FuselageConfig(**kwargs) if kwargs else FuselageConfig()

        # Extract parameters from config
        a = config.a
        b = config.b
        T = config.T
        H = config.H
        h = config.h
        cmax = config.cmax

        # Structural layout from config
        self.Stringer_spacing = config.stringer_spacing
        self.Frame_spacing = config.frame_spacing
        self.Floor2Frame = 6 * 12 + 5
        self.Bayes_number = config.bayes_number
        self.Door_Height = 6

        # Nomenclature
        nomenclature = Nomenclature(fonction_nomenclature, 8)
        self.Nomenclature = nomenclature
        self.MAX_Length = nomenclature.MAX_Length
        self.Script_Spacing = nomenclature.Script_Spacing
        self.cmax = cmax

        # File name
        self.File_name = f'Fuselage_a{int(a)}in_b{int(b)}in_T{int(T)}in_H{int(H)}in_h{int(h)}in_c{cmax}'

        # Geometry calculations
        self.L = self.Frame_spacing * self.Bayes_number
        self.T = T
        self.E = np.sqrt(1 - min(b / a, a / b) ** 2)
        self.a = a
        self.b = b
        self.H = H
        self.h = h
        self.P = np.pi * np.sqrt(2 * (a ** 2 + b ** 2))
        self.A = np.pi * a * b
        self.R = 2 * self.A / self.P
        self.Finess = 0.5 * self.L / self.R

        # No iso-eccentric transformation (matching original behavior)
        self.ar, self.br = a, b
        self.Pr = np.pi * np.sqrt(2 * (self.ar ** 2 + self.br ** 2))
        self.Ar = np.pi * self.ar * self.br
        self.Rr = 2 * self.Ar / self.Pr
        self.Stringer_number = config.stringer_number
        self.Real_finess = 0.5 * self.L / self.Rr

        # Floor indices
        self.Floor_index1, self.Floor_index2, self.Floor_index3 = self.setup_floor_index()
        self.Hr = (self.br - self.T) * (1 - np.sin(2 * (self.Floor_index1 - 1) * np.pi / self.Stringer_number + np.pi / 2))
        self.Floor_width = abs(2 * self.ar * np.cos(2 * (self.Floor_index1 - 1) * np.pi / self.Stringer_number + np.pi / 2))

        # Materials from config
        sm = config.stringer_material
        skm = config.skin_material
        fm = config.frame_material
        self.StringerMat = MAT1(1, sm.E, sm.G, sm.NU, sm.RHO, None, None, None, None, None, None, None, self.Script_Spacing)
        self.SkinMat = MAT1(2, skm.E, skm.G, skm.NU, skm.RHO, None, None, None, None, None, None, None, self.Script_Spacing)
        self.FrameMat = MAT1(3, fm.E, fm.G, fm.NU, fm.RHO, None, None, None, None, None, None, None, self.Script_Spacing)

        # Section properties from config
        sec = config.sections
        self.Skin_N = PSHELL(11, 2, sec.skin_thickness, None, None, None, None, None, None, None, None, self.Script_Spacing, (0, 1, 1), (0, 0, 1))
        self.Stringer_N = PROD(21, 1, sec.stringer_area, None, None, None, self.Script_Spacing, (1, 1, 0))
        self.Frame_N = PSHELL(31, 3, sec.frame_web_thickness, None, None, None, None, None, None, None, None, self.Script_Spacing, (0.2, 0.2, 0.2), (0.5, 0, 0.5))
        self.Frame_edge_N1 = PROD(32, 3, sec.frame_edge_area_inner, None, None, None, self.Script_Spacing, (0, 0.8, 0))
        self.Frame_edge_N2 = PROD(33, 3, sec.frame_edge_area_outer, None, None, None, self.Script_Spacing, (0.2, 1, 0.2))
        self.Floor_L = PSHELL(41, 3, sec.floor_long_thickness, None, None, None, None, None, None, None, None, self.Script_Spacing, (0.2, 0.2, 0.2), (0.5, 0, 0.5))
        self.Floor_T = PSHELL(42, 3, sec.floor_trans_thickness, None, None, None, None, None, None, None, None, self.Script_Spacing, (0.2, 0.2, 0.2), (0.5, 0, 0.5))
        self.Floor_L_edge_Top = PROD(43, 3, sec.floor_long_edge_top_area, None, None, None, self.Script_Spacing, (0, 0.4, 0.4))
        self.Floor_L_edge_Bot = PROD(44, 3, sec.floor_long_edge_bot_area, None, None, None, self.Script_Spacing, (0, 0.4, 0.4))
        self.Floor_T_edge_Top = PROD(45, 3, sec.floor_trans_edge_top_area, None, None, None, self.Script_Spacing, (0, 0.8, 0.8))
        self.Floor_T_edge_Bot = PROD(46, 3, sec.floor_trans_edge_bot_area, None, None, None, self.Script_Spacing, (0, 0.8, 0.8))
        self.Floor_Post = PROD(47, 3, sec.floor_post_area, None, None, None, self.Script_Spacing, (0, 0.8, 0.8))

        # Warnings
        self._warnings = []
        if 2 * self.Stringer_number > 999:
            self._warnings.append("GRID NUMBER ABOVE LIMIT!")
        if self.Hr < self.Floor2Frame:
            self._warnings.append(f"Unexpected floor height: Hr = {self.Hr:.3f} < {self.Floor2Frame}")

    @property
    def warnings(self):
        return self._warnings

    def build_skin_p(self):
        return [GRID(
            self.Nomenclature.func("GRID", [frame, self.cmax, i]),
            None,
            self.ar * np.cos(2 * (i - 1) * np.pi / self.Stringer_number + np.pi / 2),
            self.br * np.sin(2 * (i - 1) * np.pi / self.Stringer_number + np.pi / 2),
            (frame - 1) * self.Frame_spacing,
            None, None, self.Script_Spacing)
            for frame in range(1, self.Bayes_number + 2)
            for i in range(1, self.Stringer_number + 1)]

    def build_frames_p(self):
        frame_offset = 3
        return [GRID(
            self.Nomenclature.func("GRID", [frame, self.cmax - 1, i]),
            None,
            (self.ar - frame_offset) * np.cos(2 * (i - 1) * np.pi / self.Stringer_number + np.pi / 2),
            (self.br - frame_offset) * np.sin(2 * (i - 1) * np.pi / self.Stringer_number + np.pi / 2),
            (frame - 1) * self.Frame_spacing,
            None, None, self.Script_Spacing)
            for frame in range(1, self.Bayes_number + 2)
            for i in range(1, self.Stringer_number + 1)]

    def build_stringers(self):
        return [CROD(
            self.Nomenclature.func("CROD", [frame, frame + 1, self.cmax, i, i]),
            self.Stringer_N.PID,
            self.Nomenclature.func("GRID", [frame, self.cmax, i]),
            self.Nomenclature.func("GRID", [frame + 1, self.cmax, i]),
            self.Script_Spacing)
            for frame in range(1, self.Bayes_number + 1)
            for i in range(1, self.Stringer_number + 1)]

    def build_frames_e(self):
        L = [CROD(
            self.Nomenclature.func("CROD", [frame, frame, self.cmax - 1, i, i + 1]),
            self.Frame_edge_N1.PID,
            self.Nomenclature.func("GRID", [frame, self.cmax - 1, i]),
            self.Nomenclature.func("GRID", [frame, self.cmax - 1, i + 1]),
            self.Script_Spacing)
            if i < self.Stringer_number
            else
            CROD(
                self.Nomenclature.func("CROD", [frame, frame, self.cmax - 1, i, 1]),
                self.Frame_edge_N1.PID,
                self.Nomenclature.func("GRID", [frame, self.cmax - 1, i]),
                self.Nomenclature.func("GRID", [frame, self.cmax - 1, 1]),
                self.Script_Spacing)
            for frame in range(1, self.Bayes_number + 2)
            for i in range(1, self.Stringer_number + 1)]
        L.extend([CROD(
            self.Nomenclature.func("CROD", [frame, frame, self.cmax, i, i + 1]),
            self.Frame_edge_N2.PID,
            self.Nomenclature.func("GRID", [frame, self.cmax, i]),
            self.Nomenclature.func("GRID", [frame, self.cmax, i + 1]),
            self.Script_Spacing)
            if i < self.Stringer_number
            else
            CROD(
                self.Nomenclature.func("CROD", [frame, frame, self.cmax, i, 1]),
                self.Frame_edge_N2.PID,
                self.Nomenclature.func("GRID", [frame, self.cmax, i]),
                self.Nomenclature.func("GRID", [frame, self.cmax, 1]),
                self.Script_Spacing)
            for frame in range(1, self.Bayes_number + 2)
            for i in range(1, self.Stringer_number + 1)])
        return L

    def build_skin(self):
        return [CQUAD4(
            self.Nomenclature.func("CQUAD4", [frame + self.Bayes_number + 1, frame + 1 + self.Bayes_number + 1, self.cmax, i, i, i + 1, i + 1]),
            self.Skin_N.PID,
            self.Nomenclature.func("GRID", [frame, self.cmax, i]),
            self.Nomenclature.func("GRID", [frame + 1, self.cmax, i]),
            self.Nomenclature.func("GRID", [frame + 1, self.cmax, i + 1]),
            self.Nomenclature.func("GRID", [frame, self.cmax, i + 1]),
            None, None, self.Script_Spacing)
            if i < self.Stringer_number
            else
            CQUAD4(
                self.Nomenclature.func("CQUAD4", [frame + self.Bayes_number + 1, frame + 1 + self.Bayes_number + 1, self.cmax, i, i, 1, 1]),
                self.Skin_N.PID,
                self.Nomenclature.func("GRID", [frame, self.cmax, i]),
                self.Nomenclature.func("GRID", [frame + 1, self.cmax, i]),
                self.Nomenclature.func("GRID", [frame + 1, self.cmax, 1]),
                self.Nomenclature.func("GRID", [frame, self.cmax, 1]),
                None, None, self.Script_Spacing)
            for frame in range(1, self.Bayes_number + 1)
            for i in range(1, self.Stringer_number + 1)]

    def build_frames(self):
        return [CQUAD4(
            self.Nomenclature.func("CQUAD4", [frame + self.Bayes_number + 1, frame + self.Bayes_number + 1, self.cmax - 1, i, i, i + 1, i + 1]),
            self.Frame_N.PID,
            self.Nomenclature.func("GRID", [frame, self.cmax - 1, i]),
            self.Nomenclature.func("GRID", [frame, self.cmax, i]),
            self.Nomenclature.func("GRID", [frame, self.cmax, i + 1]),
            self.Nomenclature.func("GRID", [frame, self.cmax - 1, i + 1]),
            None, None, self.Script_Spacing)
            if i < self.Stringer_number
            else
            CQUAD4(
                self.Nomenclature.func("CQUAD4", [frame + self.Bayes_number + 1, frame + self.Bayes_number + 1, self.cmax - 1, i, i, 1, 1]),
                self.Frame_N.PID,
                self.Nomenclature.func("GRID", [frame, self.cmax - 1, i]),
                self.Nomenclature.func("GRID", [frame, self.cmax, i]),
                self.Nomenclature.func("GRID", [frame, self.cmax, 1]),
                self.Nomenclature.func("GRID", [frame, self.cmax - 1, 1]),
                None, None, self.Script_Spacing)
            for frame in range(1, self.Bayes_number + 2)
            for i in range(1, self.Stringer_number + 1)]

    def build_floor_p(self):
        L = []
        for frame in range(1, self.Bayes_number + 2):
            for crown in range(1, self.cmax - 1):
                P1 = GRID(self.Nomenclature.func("GRID", [frame, crown, 1]), None,
                          -0.5 * self.Floor_width * crown / (self.cmax - 1),
                          self.br - self.T - self.Hr,
                          (frame - 1) * self.Frame_spacing, None, None, self.Script_Spacing)
                P2 = GRID(self.Nomenclature.func("GRID", [frame, crown, 2]), None,
                          -0.5 * self.Floor_width * crown / (self.cmax - 1),
                          self.br - self.T - self.Hr - self.h,
                          (frame - 1) * self.Frame_spacing, None, None, self.Script_Spacing)
                P3 = GRID(self.Nomenclature.func("GRID", [frame, crown, 3]), None,
                          0.5 * self.Floor_width * crown / (self.cmax - 1),
                          self.br - self.T - self.Hr - self.h,
                          (frame - 1) * self.Frame_spacing, None, None, self.Script_Spacing)
                P4 = GRID(self.Nomenclature.func("GRID", [frame, crown, 4]), None,
                          0.5 * self.Floor_width * crown / (self.cmax - 1),
                          self.br - self.T - self.Hr,
                          (frame - 1) * self.Frame_spacing, None, None, self.Script_Spacing)
                L.extend([P1, P2, P3, P4])
        return L

    def build_floor_e(self):
        L = [CROD(self.Nomenclature.func("CROD", [frame, frame, 0, 2, 3]),
                  self.Floor_L_edge_Bot.PID,
                  self.Nomenclature.func("GRID", [frame, 1, 2]),
                  self.Nomenclature.func("GRID", [frame, 1, 3]),
                  self.Script_Spacing)
             for frame in range(1, self.Bayes_number + 2)]
        L.extend([CROD(self.Nomenclature.func("CROD", [frame, frame, 0, 1, 4]),
                       self.Floor_L_edge_Top.PID,
                       self.Nomenclature.func("GRID", [frame, 1, 1]),
                       self.Nomenclature.func("GRID", [frame, 1, 4]),
                       self.Script_Spacing)
                  for frame in range(1, self.Bayes_number + 2)])
        L.extend([CROD(self.Nomenclature.func("CROD", [frame, frame, crown, 2, 2]),
                       self.Floor_L_edge_Bot.PID,
                       self.Nomenclature.func("GRID", [frame, crown, 2]),
                       self.Nomenclature.func("GRID", [frame, crown + 1, 2]),
                       self.Script_Spacing)
                  for frame in range(1, self.Bayes_number + 2)
                  for crown in range(1, self.cmax - 2)])
        L.extend([CROD(self.Nomenclature.func("CROD", [frame, frame, crown, 1, 1]),
                       self.Floor_L_edge_Top.PID,
                       self.Nomenclature.func("GRID", [frame, crown, 1]),
                       self.Nomenclature.func("GRID", [frame, crown + 1, 1]),
                       self.Script_Spacing)
                  for frame in range(1, self.Bayes_number + 2)
                  for crown in range(1, self.cmax - 2)])
        L.extend([CROD(self.Nomenclature.func("CROD", [frame, frame, self.cmax - 2, 2, self.Floor_index2]),
                       self.Floor_L_edge_Bot.PID,
                       self.Nomenclature.func("GRID", [frame, self.cmax - 2, 2]),
                       self.Nomenclature.func("GRID", [frame, self.cmax - 1, self.Floor_index2]),
                       self.Script_Spacing)
                  for frame in range(1, self.Bayes_number + 2)])
        L.extend([CROD(self.Nomenclature.func("CROD", [frame, frame, self.cmax - 2, 1, self.Floor_index1]),
                       self.Floor_L_edge_Top.PID,
                       self.Nomenclature.func("GRID", [frame, self.cmax - 2, 1]),
                       self.Nomenclature.func("GRID", [frame, self.cmax - 1, self.Floor_index1]),
                       self.Script_Spacing)
                  for frame in range(1, self.Bayes_number + 2)])
        L.extend([CROD(self.Nomenclature.func("CROD", [frame, frame, crown, 3, 3]),
                       self.Floor_L_edge_Bot.PID,
                       self.Nomenclature.func("GRID", [frame, crown, 3]),
                       self.Nomenclature.func("GRID", [frame, crown + 1, 3]),
                       self.Script_Spacing)
                  for frame in range(1, self.Bayes_number + 2)
                  for crown in range(1, self.cmax - 2)])
        L.extend([CROD(self.Nomenclature.func("CROD", [frame, frame, crown, 4, 4]),
                       self.Floor_L_edge_Top.PID,
                       self.Nomenclature.func("GRID", [frame, crown, 4]),
                       self.Nomenclature.func("GRID", [frame, crown + 1, 4]),
                       self.Script_Spacing)
                  for frame in range(1, self.Bayes_number + 2)
                  for crown in range(1, self.cmax - 2)])
        L.extend([CROD(self.Nomenclature.func("CROD", [frame, frame, self.cmax - 2, 3, self.Stringer_number - self.Floor_index2 + 2]),
                       self.Floor_L_edge_Bot.PID,
                       self.Nomenclature.func("GRID", [frame, self.cmax - 2, 3]),
                       self.Nomenclature.func("GRID", [frame, self.cmax - 1, self.Stringer_number - self.Floor_index2 + 2]),
                       self.Script_Spacing)
                  for frame in range(1, self.Bayes_number + 2)])
        L.extend([CROD(self.Nomenclature.func("CROD", [frame, frame, self.cmax - 2, 4, self.Stringer_number - self.Floor_index1 + 2]),
                       self.Floor_L_edge_Top.PID,
                       self.Nomenclature.func("GRID", [frame, self.cmax - 2, 4]),
                       self.Nomenclature.func("GRID", [frame, self.cmax - 1, self.Stringer_number - self.Floor_index1 + 2]),
                       self.Script_Spacing)
                  for frame in range(1, self.Bayes_number + 2)])
        L.extend([CROD(self.Nomenclature.func("CROD", [frame, frame + 1, crown, 2, 2]),
                       self.Floor_T_edge_Bot.PID,
                       self.Nomenclature.func("GRID", [frame, crown, 2]),
                       self.Nomenclature.func("GRID", [frame + 1, crown, 2]),
                       self.Script_Spacing)
                  for frame in range(1, self.Bayes_number + 1)
                  for crown in range(1, self.cmax - 1)])
        L.extend([CROD(self.Nomenclature.func("CROD", [frame, frame + 1, crown, 1, 1]),
                       self.Floor_T_edge_Top.PID,
                       self.Nomenclature.func("GRID", [frame, crown, 1]),
                       self.Nomenclature.func("GRID", [frame + 1, crown, 1]),
                       self.Script_Spacing)
                  for frame in range(1, self.Bayes_number + 1)
                  for crown in range(1, self.cmax - 1)])
        L.extend([CROD(self.Nomenclature.func("CROD", [frame, frame + 1, crown, 3, 3]),
                       self.Floor_T_edge_Bot.PID,
                       self.Nomenclature.func("GRID", [frame, crown, 3]),
                       self.Nomenclature.func("GRID", [frame + 1, crown, 3]),
                       self.Script_Spacing)
                  for frame in range(1, self.Bayes_number + 1)
                  for crown in range(1, self.cmax - 1)])
        L.extend([CROD(self.Nomenclature.func("CROD", [frame, frame + 1, crown, 4, 4]),
                       self.Floor_T_edge_Top.PID,
                       self.Nomenclature.func("GRID", [frame, crown, 4]),
                       self.Nomenclature.func("GRID", [frame + 1, crown, 4]),
                       self.Script_Spacing)
                  for frame in range(1, self.Bayes_number + 1)
                  for crown in range(1, self.cmax - 1)])
        L.extend([CROD(self.Nomenclature.func("CROD", [frame, frame, 1, self.Floor_index3, 2]),
                       self.Floor_Post.PID,
                       self.Nomenclature.func("GRID", [frame, self.cmax - 1, self.Floor_index3]),
                       self.Nomenclature.func("GRID", [frame, 1, 2]),
                       self.Script_Spacing)
                  for frame in range(1, self.Bayes_number + 2)])
        L.extend([CROD(self.Nomenclature.func("CROD", [frame, frame, 1, self.Stringer_number - self.Floor_index3 + 2, 3]),
                       self.Floor_Post.PID,
                       self.Nomenclature.func("GRID", [frame, self.cmax - 1, self.Stringer_number - self.Floor_index3 + 2]),
                       self.Nomenclature.func("GRID", [frame, 1, 3]),
                       self.Script_Spacing)
                  for frame in range(1, self.Bayes_number + 2)])
        return L

    def build_floor(self):
        L = [CQUAD4(
            self.Nomenclature.func("CQUAD4", [frame + self.Bayes_number + 1, frame + self.Bayes_number + 1, 0, 1, 2, 3, 4]),
            self.Floor_L.PID,
            self.Nomenclature.func("GRID", [frame, 1, 1]),
            self.Nomenclature.func("GRID", [frame, 1, 2]),
            self.Nomenclature.func("GRID", [frame, 1, 3]),
            self.Nomenclature.func("GRID", [frame, 1, 4]),
            None, None, self.Script_Spacing)
            for frame in range(1, self.Bayes_number + 2)]
        L.extend([CQUAD4(
            self.Nomenclature.func("CQUAD4", [frame + self.Bayes_number + 1, frame + self.Bayes_number + 1, crown, 1, 1, 2, 2]),
            self.Floor_L.PID,
            self.Nomenclature.func("GRID", [frame, crown, 1]),
            self.Nomenclature.func("GRID", [frame, crown + 1, 1]),
            self.Nomenclature.func("GRID", [frame, crown + 1, 2]),
            self.Nomenclature.func("GRID", [frame, crown, 2]),
            None, None, self.Script_Spacing)
            for frame in range(1, self.Bayes_number + 2)
            for crown in range(1, self.cmax - 2)])
        L.extend([CQUAD4(
            self.Nomenclature.func("CQUAD4", [frame + self.Bayes_number + 1, frame + self.Bayes_number + 1, self.cmax - 2, 1, self.Floor_index1, self.Floor_index2, 2]),
            self.Floor_L.PID,
            self.Nomenclature.func("GRID", [frame, self.cmax - 2, 1]),
            self.Nomenclature.func("GRID", [frame, self.cmax - 1, self.Floor_index1]),
            self.Nomenclature.func("GRID", [frame, self.cmax - 1, self.Floor_index2]),
            self.Nomenclature.func("GRID", [frame, self.cmax - 2, 2]),
            None, None, self.Script_Spacing)
            for frame in range(1, self.Bayes_number + 2)])
        L.extend([CQUAD4(
            self.Nomenclature.func("CQUAD4", [frame + self.Bayes_number + 1, frame + self.Bayes_number + 1, crown, 4, 4, 3, 3]),
            self.Floor_L.PID,
            self.Nomenclature.func("GRID", [frame, crown, 4]),
            self.Nomenclature.func("GRID", [frame, crown + 1, 4]),
            self.Nomenclature.func("GRID", [frame, crown + 1, 3]),
            self.Nomenclature.func("GRID", [frame, crown, 3]),
            None, None, self.Script_Spacing)
            for frame in range(1, self.Bayes_number + 2)
            for crown in range(1, self.cmax - 2)])
        L.extend([CQUAD4(
            self.Nomenclature.func("CQUAD4", [frame + self.Bayes_number + 1, frame + self.Bayes_number + 1, self.cmax - 2, 4, self.Stringer_number - self.Floor_index1 + 2, self.Stringer_number - self.Floor_index2 + 2, 3]),
            self.Floor_L.PID,
            self.Nomenclature.func("GRID", [frame, self.cmax - 2, 4]),
            self.Nomenclature.func("GRID", [frame, self.cmax - 1, self.Stringer_number - self.Floor_index1 + 2]),
            self.Nomenclature.func("GRID", [frame, self.cmax - 1, self.Stringer_number - self.Floor_index2 + 2]),
            self.Nomenclature.func("GRID", [frame, self.cmax - 2, 3]),
            None, None, self.Script_Spacing)
            for frame in range(1, self.Bayes_number + 2)])
        L.extend([CQUAD4(
            self.Nomenclature.func("CQUAD4", [frame + self.Bayes_number + 1, frame + 1 + self.Bayes_number + 1, crown, 1, 2, 2, 1]),
            self.Floor_T.PID,
            self.Nomenclature.func("GRID", [frame, crown, 1]),
            self.Nomenclature.func("GRID", [frame, crown, 2]),
            self.Nomenclature.func("GRID", [frame + 1, crown, 2]),
            self.Nomenclature.func("GRID", [frame + 1, crown, 1]),
            None, None, self.Script_Spacing)
            for frame in range(1, self.Bayes_number + 1)
            for crown in range(1, self.cmax - 1)])
        L.extend([CQUAD4(
            self.Nomenclature.func("CQUAD4", [frame + self.Bayes_number + 1, frame + 1 + self.Bayes_number + 1, crown, 4, 3, 3, 4]),
            self.Floor_T.PID,
            self.Nomenclature.func("GRID", [frame, crown, 4]),
            self.Nomenclature.func("GRID", [frame, crown, 3]),
            self.Nomenclature.func("GRID", [frame + 1, crown, 3]),
            self.Nomenclature.func("GRID", [frame + 1, crown, 4]),
            None, None, self.Script_Spacing)
            for frame in range(1, self.Bayes_number + 1)
            for crown in range(1, self.cmax - 1)])
        return L

    def build_FEM(self, progress_callback=None):
        """Build the complete FEM model.

        Args:
            progress_callback: Optional callable(percent: int, message: str) for progress updates.
        """
        Name = f"Fuselage ar ~ {round(self.ar, 5)} m, br ~ {round(self.br, 5)} m, T = {self.T} m, Hr ~ {round(self.Hr, 5)} m, h = {self.h} m and cmax = {self.cmax}"

        if progress_callback:
            progress_callback(0, "Building reference node...")

        GRID_List = [GRID(
            self.Nomenclature.func("GRID", [self.Bayes_number + 1, 0, 1]),
            None, 0, 0, self.Bayes_number * self.Frame_spacing,
            None, None, self.Script_Spacing)]

        if progress_callback:
            progress_callback(5, "Building skin points...")
        GRID_List.extend(self.build_skin_p())

        if progress_callback:
            progress_callback(15, "Building frame points...")
        GRID_List.extend(self.build_frames_p())

        MAT_List = [self.StringerMat, self.SkinMat, self.FrameMat]
        PSHELL_List = [self.Skin_N, self.Frame_N]
        PROD_List = [self.Stringer_N, self.Frame_edge_N1, self.Frame_edge_N2]

        if progress_callback:
            progress_callback(25, "Building stringers...")
        CROD_List = self.build_stringers()

        if progress_callback:
            progress_callback(35, "Building frame edges...")
        CROD_List.extend(self.build_frames_e())

        if progress_callback:
            progress_callback(50, "Building skin panels...")
        CQUAD4_List = self.build_skin()

        if progress_callback:
            progress_callback(65, "Building frame panels...")
        CQUAD4_List.extend(self.build_frames())

        if progress_callback:
            progress_callback(75, "Building floor structure...")
        if self.cmax > 2 and self.Hr > 0 and 2 * self.br > self.Hr and self.h > 0:
            PSHELL_List.extend([self.Floor_L, self.Floor_T])
            PROD_List.extend([self.Floor_L_edge_Top, self.Floor_L_edge_Bot,
                              self.Floor_T_edge_Top, self.Floor_T_edge_Bot, self.Floor_Post])
            GRID_List.extend(self.build_floor_p())
            CROD_List.extend(self.build_floor_e())
            CQUAD4_List.extend(self.build_floor())

        if self.Hr > 2 * self.br:
            self._warnings.append(f"Could not build floor: 2br = {2 * self.br:.3f} < Hr = {self.Hr:.3f}")

        MPC_List = []
        SPC_List = []

        if progress_callback:
            progress_callback(95, "Assembling FEM model...")

        fem = FEM(Name, GRID_List, MPC_List, MAT_List, PROD_List,
                  PSHELL_List, CROD_List, CQUAD4_List, SPC_List, self.File_name)

        if progress_callback:
            progress_callback(100, "Complete.")

        return fem


if __name__ == "__main__":
    config = FuselageConfig(a=46, b=46, T=0.04, H=46 * 2 - 3 * 12 + 6, h=3, cmax=4)
    fus = Fuselage(config)
    fem = fus.build_FEM()
    print(fem)
    result = fem.generate_NASTRAN_build()
    print(result)
