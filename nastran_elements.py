"""NASTRAN finite element classes for fuselage FEM generation.

Refactored from Classes_Nastran.py:
- Removed Mayavi dependency (visualization handled by renderer.py)
- Cached dictionary lookups in FEM.get_object()
- Parameterized generate_NASTRAN_build() file path
- All __repr__ methods preserved exactly for .dat export compatibility
"""

import numpy as np


class MAT1:
    """NASTRAN MAT1 material definition card."""

    def __init__(self, MID, E, G, NU, RHO, A, TREF, GE, ST, SC, SS, MCSID, Script_Spacing):
        self.MID = MID
        self.E = E
        self.G = G
        self.NU = NU
        self.RHO = RHO
        self.A = A
        self.TREF = TREF
        self.GE = GE
        self.ST = ST
        self.SC = SC
        self.SS = SS
        self.MCSID = MCSID

        self.Script_Spacing = Script_Spacing
        self.fill = ' ' * self.Script_Spacing

    def __repr__(self):
        MID = str(self.MID).rjust(self.Script_Spacing) if self.MID is not None else self.fill
        E = str(self.E).rjust(self.Script_Spacing) if self.E is not None else self.fill
        G = str(self.G).rjust(self.Script_Spacing) if self.G is not None else self.fill
        NU = str(self.NU).rjust(self.Script_Spacing) if self.NU is not None else self.fill
        RHO = str(self.RHO).rjust(self.Script_Spacing) if self.RHO is not None else self.fill
        A = str(self.A).rjust(self.Script_Spacing) if self.A is not None else self.fill
        TREF = str(self.TREF).rjust(self.Script_Spacing) if self.TREF is not None else self.fill
        GE = str(self.GE).rjust(self.Script_Spacing) if self.GE is not None else self.fill
        ST = str(self.ST).rjust(self.Script_Spacing) if self.ST is not None else self.fill
        SC = str(self.SC).rjust(self.Script_Spacing) if self.SC is not None else self.fill
        SS = str(self.SS).rjust(self.Script_Spacing) if self.SS is not None else self.fill
        MCSID = str(self.MCSID).rjust(self.Script_Spacing) if self.MCSID is not None else self.fill
        return f"MAT1,\t{MID},\t{E},\t{G},\t{NU},\t{RHO},\t{A},\t{TREF},\t{GE},\n    ,\t{ST},\t{SC},\t{SS},\t{MCSID}"


class GRID:
    """NASTRAN GRID node definition card."""

    def __init__(self, ID, CP, X1, X2, X3, CD, PSPC, Script_Spacing):
        self.ID = ID
        self.CP = CP
        self.X1 = X1
        self.X2 = X2
        self.X3 = X3
        self.CD = CD
        self.PSPC = PSPC

        self.Script_Spacing = Script_Spacing
        self.fill = ' ' * self.Script_Spacing
        self.flim = Script_Spacing - 4

    def __repr__(self):
        ID = str(self.ID).rjust(self.Script_Spacing) if self.ID is not None else self.fill
        CP = str(self.CP).rjust(self.Script_Spacing) if self.CP is not None else self.fill
        X1 = str(round(float(self.X1), self.flim)).rjust(self.Script_Spacing) if self.X1 is not None else self.fill
        X2 = str(round(float(self.X2), self.flim)).rjust(self.Script_Spacing) if self.X2 is not None else self.fill
        X3 = str(round(float(self.X3), self.flim)).rjust(self.Script_Spacing) if self.X3 is not None else self.fill
        CD = str(self.CD).rjust(self.Script_Spacing) if self.CD is not None else self.fill
        PSPC = str(self.PSPC).rjust(self.Script_Spacing) if self.PSPC is not None else self.fill
        return f"GRID,\t{ID},\t{CP},\t{X1},\t{X2},\t{X3},\t{CD},\t{PSPC}"

    def get_point(self):
        return [self.ID, self.X1, self.X2, self.X3]


class PROD:
    """NASTRAN PROD rod property definition card."""

    def __init__(self, PID, MID, A, J, C, NSM, Script_Spacing, color):
        self.PID = PID
        self.MID = MID
        self.A = A
        self.J = J
        self.C = C
        self.NSM = NSM

        self.Script_Spacing = Script_Spacing
        self.fill = ' ' * self.Script_Spacing
        self.color = color

    def __repr__(self):
        PID = str(self.PID).rjust(self.Script_Spacing) if self.PID is not None else self.fill
        MID = str(self.MID).rjust(self.Script_Spacing) if self.MID is not None else self.fill
        A = str(self.A).rjust(self.Script_Spacing) if self.A is not None else self.fill
        J = str(self.J).rjust(self.Script_Spacing) if self.J is not None else self.fill
        C = str(self.C).rjust(self.Script_Spacing) if self.C is not None else self.fill
        NSM = str(self.NSM).rjust(self.Script_Spacing) if self.NSM is not None else self.fill
        return f"PROD,\t{PID},\t{MID},\t{A},\t{J},\t{C},\t{NSM}"


class CROD:
    """NASTRAN CROD rod element card."""

    def __init__(self, EID, PID, G1, G2, Script_Spacing):
        self.EID = EID
        self.PID = PID
        self.G1 = G1
        self.G2 = G2

        self.Script_Spacing = Script_Spacing
        self.fill = ' ' * self.Script_Spacing

    def __repr__(self):
        EID = str(self.EID).rjust(self.Script_Spacing) if self.EID is not None else self.fill
        PID = str(self.PID).rjust(self.Script_Spacing) if self.PID is not None else self.fill
        G1 = str(self.G1).rjust(self.Script_Spacing) if self.G1 is not None else self.fill
        G2 = str(self.G2).rjust(self.Script_Spacing) if self.G2 is not None else self.fill
        return f"CROD,\t{EID},\t{PID},\t{G1},\t{G2}"


class PSHELL:
    """NASTRAN PSHELL shell property definition card."""

    def __init__(self, PID, MID1, T, MID2, Ri, MID3, Rs, NSM, Z1, Z2, MID4, Script_Spacing, color, edge_color):
        self.PID = PID
        self.MID1 = MID1
        self.T = T
        self.MID2 = MID2
        self.Ri = Ri
        self.MID3 = MID3
        self.Rs = Rs
        self.NSM = NSM
        self.Z1 = Z1
        self.Z2 = Z2
        self.MID4 = MID4

        self.Script_Spacing = Script_Spacing
        self.fill = ' ' * self.Script_Spacing
        self.color = color
        self.edge_color = edge_color

    def __repr__(self):
        PID = str(self.PID).rjust(self.Script_Spacing) if self.PID is not None else self.fill
        MID1 = str(self.MID1).rjust(self.Script_Spacing) if self.MID1 is not None else self.fill
        T = str(self.T).rjust(self.Script_Spacing) if self.T is not None else self.fill
        MID2 = str(self.MID2).rjust(self.Script_Spacing) if self.MID2 is not None else self.fill
        Ri = str(self.Ri).rjust(self.Script_Spacing) if self.Ri is not None else self.fill
        MID3 = str(self.MID3).rjust(self.Script_Spacing) if self.MID3 is not None else self.fill
        Rs = str(self.Rs).rjust(self.Script_Spacing) if self.Rs is not None else self.fill
        NSM = str(self.NSM).rjust(self.Script_Spacing) if self.NSM is not None else self.fill
        Z1 = str(self.Z1).rjust(self.Script_Spacing) if self.Z1 is not None else self.fill
        Z2 = str(self.Z2).rjust(self.Script_Spacing) if self.Z2 is not None else self.fill
        MID4 = str(self.MID4).rjust(self.Script_Spacing) if self.MID4 is not None else self.fill
        return f"PSHELL,\t{PID},\t{MID1},\t{T},\t{MID2},\t{Ri},\t{MID3},\t{Rs},\t{NSM},\n      ,\t{Z1},\t{Z2},\t{MID4}"


class CQUAD4:
    """NASTRAN CQUAD4 4-node quad shell element card."""

    def __init__(self, EID, PID, G1, G2, G3, G4, THETA, ZOFF, Script_Spacing):
        self.EID = EID
        self.PID = PID
        self.G1 = G1
        self.G2 = G2
        self.G3 = G3
        self.G4 = G4
        self.THETA = THETA
        self.ZOFF = ZOFF

        self.Script_Spacing = Script_Spacing
        self.fill = ' ' * self.Script_Spacing

    def __repr__(self):
        EID = str(self.EID).rjust(self.Script_Spacing) if self.EID is not None else self.fill
        PID = str(self.PID).rjust(self.Script_Spacing) if self.PID is not None else self.fill
        G1 = str(self.G1).rjust(self.Script_Spacing) if self.G1 is not None else self.fill
        G2 = str(self.G2).rjust(self.Script_Spacing) if self.G2 is not None else self.fill
        G3 = str(self.G3).rjust(self.Script_Spacing) if self.G3 is not None else self.fill
        G4 = str(self.G4).rjust(self.Script_Spacing) if self.G4 is not None else self.fill
        THETA = str(self.THETA).rjust(self.Script_Spacing) if self.THETA is not None else self.fill
        ZOFF = str(self.ZOFF).rjust(self.Script_Spacing) if self.ZOFF is not None else self.fill
        return f"CQUAD4,\t{EID},\t{PID},\t{G1},\t{G2},\t{G3},\t{G4},\t{THETA},\t{ZOFF}\n      ,\t{self.fill},\t{self.fill},\t{self.fill},\t{self.fill},\t{self.fill},"


class MPC:
    """NASTRAN MPC multi-point constraint card."""

    def __init__(self, SID, Ge, Ce, Ae, G_List, C_List, A_List, Script_Spacing, color):
        self.SID = SID
        self.Ge = Ge
        self.Ce = Ce
        self.Ae = Ae
        self.G_List = G_List
        self.C_List = C_List
        self.A_List = A_List

        self.Script_Spacing = Script_Spacing
        self.fill = ' ' * self.Script_Spacing
        self.color = color
        self.num_segments = 50

    def __repr__(self):
        SID = str(self.SID).rjust(self.Script_Spacing) if self.SID is not None else self.fill
        Ge = str(self.Ge).rjust(self.Script_Spacing) if self.Ge is not None else self.fill
        Ce = str(self.Ce).rjust(self.Script_Spacing) if self.Ce is not None else self.fill
        Ae = str(self.Ae).rjust(self.Script_Spacing) if self.Ae is not None else self.fill
        G_List = [str(elt).rjust(self.Script_Spacing) for elt in self.G_List] if self.G_List is not None else [self.fill]
        C_List = [str(elt).rjust(self.Script_Spacing) for elt in self.C_List] if self.C_List is not None else [self.fill]
        A_List = [str(elt).rjust(self.Script_Spacing) for elt in self.A_List] if self.A_List is not None else [self.fill]
        ans = f"MPC,\t{SID},\t{Ge},\t{Ce},\t{Ae}"
        for i, (G_i, C_i, A_i) in enumerate(zip(G_List, C_List, A_List)):
            if i == 0:
                ans += f",\t{G_i},\t{C_i},\t{A_i}"
            else:
                if i % 2 == 1:
                    ans += f",\n   ,\t{self.fill},\t{G_i},\t{C_i},\t{A_i}"
                else:
                    ans += f",\t{G_i},\t{C_i},\t{A_i}"
        return ans

    def get_bars(self, fem):
        X, Y, Z = [], [], []
        ref = fem.get_object("GRID", self.Ge)
        if ref is not None:
            Xe, Ye, Ze = ref.X1, ref.X2, ref.X3
            for ID in self.G_List:
                ref2 = fem.get_object("GRID", ID)
                if ref2 is not None:
                    x_segments = [Xe + (j / (4 * self.num_segments)) * (ref2.X1 - Xe) if j % 4 != 3 else np.nan for j in range(4 * self.num_segments)]
                    y_segments = [Ye + (j / (4 * self.num_segments)) * (ref2.X2 - Ye) if j % 4 != 3 else np.nan for j in range(4 * self.num_segments)]
                    z_segments = [Ze + (j / (4 * self.num_segments)) * (ref2.X3 - Ze) if j % 4 != 3 else np.nan for j in range(4 * self.num_segments)]
                    X.extend(np.append(x_segments, np.nan))
                    Y.extend(np.append(y_segments, np.nan))
                    Z.extend(np.append(z_segments, np.nan))
        return X, Y, Z


class SPC1:
    """NASTRAN SPC1 single-point constraint card."""

    def __init__(self, SID, C, G_List, Script_Spacing):
        self.SID = SID
        self.C = C
        self.G_List = G_List

        self.Script_Spacing = Script_Spacing
        self.fill = ' ' * self.Script_Spacing

    def __repr__(self):
        SID = str(self.SID).rjust(self.Script_Spacing) if self.SID is not None else self.fill
        C = str(self.C).rjust(self.Script_Spacing) if self.C is not None else self.fill
        G_List = [str(self.G_List[elt]).rjust(self.Script_Spacing) for elt in self.G_List] if self.G_List is not None else [self.fill]
        ans = f"SPC1,\t{SID},\t{C}"
        for i, G_i in enumerate(G_List):
            if i < 5:
                ans += f",\t{G_i}"
            else:
                if (i + 5) // 6 == (i + 5) / 2:
                    ans += f",\n    ,\t{G_i}"
                else:
                    ans += f",\t{G_i}"
        return ans


class FEM:
    """Finite Element Model container with cached lookups and export capabilities."""

    def __init__(self, Name, GRID_List, MPC_List, MAT_List, PROD_List,
                 PSHELL_List, CROD_List, CQUAD4_List, SPC_List, File_name):
        self.Name = Name
        self.GRID_List = GRID_List
        self.MPC_List = MPC_List
        self.MAT_List = MAT_List
        self.PROD_List = PROD_List
        self.PSHELL_List = PSHELL_List
        self.CROD_List = CROD_List
        self.CQUAD4_List = CQUAD4_List
        self.SPC_List = SPC_List

        self.File_address = f'{File_name}.dat'

        # Pre-build lookup caches for fast get_object() calls
        self._cache = {
            "MAT1": {e.MID: e for e in self.MAT_List},
            "GRID": {e.ID: e for e in self.GRID_List},
            "MPC": {e.SID: e for e in self.MPC_List},
            "PROD": {e.PID: e for e in self.PROD_List},
            "CROD": {e.EID: e for e in self.CROD_List},
            "PSHELL": {e.PID: e for e in self.PSHELL_List},
            "CQUAD4": {e.EID: e for e in self.CQUAD4_List},
        }

    def __repr__(self):
        n_elements = len(self.CROD_List) + len(self.CQUAD4_List)
        return (
            f"FEM '{self.Name}': {len(self.GRID_List)} nodes, "
            f"{n_elements} elements ({len(self.CROD_List)} rods + "
            f"{len(self.CQUAD4_List)} quads), "
            f"{len(self.MAT_List)} materials"
        )

    @property
    def statistics(self):
        """Return model statistics dictionary for the UI."""
        return {
            "nodes": len(self.GRID_List),
            "rod_elements": len(self.CROD_List),
            "quad_elements": len(self.CQUAD4_List),
            "total_elements": len(self.CROD_List) + len(self.CQUAD4_List),
            "materials": len(self.MAT_List),
            "rod_properties": len(self.PROD_List),
            "shell_properties": len(self.PSHELL_List),
        }

    def get_object(self, Object, ID):
        """Fast cached lookup of any element by type and ID."""
        cache = self._cache.get(Object)
        if cache is not None:
            return cache.get(ID)
        return None

    def generate_NASTRAN_build(self, file_path=None):
        """Export FEM to NASTRAN .dat file."""
        path = file_path or self.File_address

        with open(path, 'w', encoding='utf-8') as nastran_doc:
            nastran_doc.write(f'$$$ ##### BEGINING DOCUMENT : {self.Name} #####\n$\n')
            nastran_doc.write('$$$ ##### BASICS #####\n$\n$\n')

            nastran_doc.write('$$$ ### POINTS ###\n$\n$\n')
            for point in self.GRID_List:
                nastran_doc.write(f'{point}\n')
            nastran_doc.write('$\n$\n')

            nastran_doc.write('$$$ ### MPCS ###\n$\n$\n')
            for mpc in self.MPC_List:
                nastran_doc.write(f'{mpc}\n')
            nastran_doc.write('$\n$\n')

            nastran_doc.write('$$$ ### MATERIALS ###\n$\n$\n')
            for mat in self.MAT_List:
                nastran_doc.write(f'{mat}\n')
            nastran_doc.write('$\n$\n')

            nastran_doc.write('$$$ ##### SECTION PROPERTIES #####\n$\n$\n')

            nastran_doc.write('$$$ ### PRODS ###\n$\n$\n')
            for prod in self.PROD_List:
                nastran_doc.write(f'{prod}\n')
            nastran_doc.write('$\n$\n')

            nastran_doc.write('$$$ ### PSHELLS ###\n$\n$\n')
            for pshell in self.PSHELL_List:
                nastran_doc.write(f'{pshell}\n')
            nastran_doc.write('$\n$\n')

            nastran_doc.write('$$$ ##### ELEMENTS #####\n$\n$\n')

            nastran_doc.write('$$$ ### CRODS ###\n$\n$\n')
            for crod in self.CROD_List:
                nastran_doc.write(f'{crod}\n')
            nastran_doc.write('$\n$\n')

            nastran_doc.write('$$$ ### CQUAD4 ###\n$\n$\n')
            for cquad4 in self.CQUAD4_List:
                nastran_doc.write(f'{cquad4}\n')
            nastran_doc.write('$\n$\n')

            nastran_doc.write('$$$ ##### FORCES & MOMENTS #####\n$\n$\n')
            nastran_doc.write('$$$ ##### BOUNDARY CONDITIONS #####\n$\n$\n')

            nastran_doc.write('$$$ ### SPCS ###\n$\n$\n')
            for spc in self.SPC_List:
                nastran_doc.write(f'{spc}\n')
            nastran_doc.write('$\n$\n')

            nastran_doc.write('$$$ ##### END OF DOCUMENT #####')

        stats = self.statistics
        return (
            f"File '{path}' successfully generated.\n"
            f"Contains:\n"
            f"\t-> {stats['materials']} materials\n"
            f"\t-> {stats['nodes']} nodes\n"
            f"\t-> {stats['total_elements']} elements\n"
            f"\t-> {stats['rod_properties'] + stats['shell_properties']} element types"
        )
