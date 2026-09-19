"""Workbook <-> Pst.

- load_table():      one sheet (or csv) as a DataFrame with upper-case headers
- to_workbook():     dump a Pst to a new workbook laid out so `build` can read it back
- update_workbook(): write values into an existing workbook, matched by PARNME / OBSNME,
                     leaving every other cell (formulas, macros, helper columns) alone
"""
import fnmatch
import os
import warnings

import pandas as pd

from .phi import ies_phi, phi_by_group
from .pst import OBS_COLS, PAR_COLS, PRIOR_COLS, Pst, read_obs_ensemble, read_par, read_res
from .sections import ALL_SECTIONS, COMPUTED, fmt

XL_ENGINE = 'openpyxl'


def load_table(spec):
    """'book.xlsx,SHEET' or 'table.csv' -> DataFrame; string headers upper-cased."""
    if ',' in spec:
        path, sheet = spec.rsplit(',', 1)
        engine = None if path.lower().endswith('.xls') else XL_ENGINE
        df = pd.read_excel(path, sheet, engine=engine)
    else:
        df = pd.read_csv(spec)
    df.columns = [c.strip().upper() if isinstance(c, str) else c for c in df.columns]
    return df


def expand_spec(spec):
    """'book.xlsx,PAR_*' -> ['book.xlsx,PAR_HK', 'book.xlsx,PAR_SY', ...] in workbook order.

    A spec without glob characters is returned as is (csv paths never expand).
    """
    if ',' not in spec:
        return [spec]
    path, pattern = spec.rsplit(',', 1)
    if not any(c in pattern for c in '*?['):
        return [spec]
    engine = None if path.lower().endswith('.xls') else XL_ENGINE
    names = pd.ExcelFile(path, engine=engine).sheet_names
    hits = [n for n in names if fnmatch.fnmatch(n.lower(), pattern.lower())]
    if not hits:
        raise ValueError(f'no sheet in {path} matches {pattern!r}; sheets: {names}')
    return [f'{path},{n}' for n in hits]


# ---------------------------------------------------------------------- dump
def control_table(pst: Pst):
    rows = []
    for sec in ALL_SECTIONS:
        for k in sec.fields:
            if k == 'pestmode':
                val = pst.pestmode
            elif k in COMPUTED:
                val = None
            else:
                val = pst.control.get(k)
            default = pst.counts.get(k, sec.defaults.get(k))
            rows.append((sec.name, k, default, val))
    return pd.DataFrame(rows, columns=['LINE', 'NAME', 'DEFAULT', 'VALUE'])


def _sheet_name(prefix, group):
    return f'{prefix}_{group}'[:31].upper()


def to_workbook(pst: Pst, path, split=False):
    """Write every table of `pst` to `path`; returns the `build` command that reads it back."""
    book = os.path.basename(path)
    par = pst.par[PAR_COLS + [c for c in ('TIETO',) if c in pst.par]]
    tables = {'CONTROL': control_table(pst), 'PARGP': pst.pargp}
    if split:
        for g, df in par.groupby('PARGP', sort=False):
            tables[_sheet_name('PAR', g)] = df
        for g, df in pst.obs.groupby('OBGNME', sort=False):
            tables[_sheet_name('OBS', g)] = df
    else:
        tables['PAR'] = par
        tables['OBS'] = pst.obs[OBS_COLS]
    if pst.nprior:
        tables['PRIOR'] = pst.prior[PRIOR_COLS]
    if pst.obs_cov:
        tables['OBSGP'] = pd.DataFrame({'OBGNME': pst.obsgp, 'COVFILE': [pst.obs_cov.get(g, '') for g in pst.obsgp]})
    tables['IO'] = pd.DataFrame([('cmd', c, '') for c in pst.cmd]
                                + [('tpl', a, b) for a, b in pst.tpl]
                                + [('ins', a, b) for a, b in pst.ins], columns=['TYPE', 'IN', 'OUT'])
    if pst.pestpp:
        tables['PP'] = pd.DataFrame(pst.pestpp, columns=['PP_VAR', 'VAL'])
    if pst.comments:
        tables['NOTES'] = pd.DataFrame({'COMMENT': pst.comments})

    cmd = [f'makepst build NEW.pst {pst.pestmode}', f'--set_ctl_xls "{book},CONTROL"']
    for name in tables:
        kind = name.split('_')[0].lower()
        if kind in ('pargp', 'par', 'obs', 'obsgp', 'prior', 'io', 'pp'):
            cmd.append(f'--add_{kind}_xls "{book},{name}"')
    if 'NOTES' in tables:
        cmd.append(f'--add_comment_xls "{book},NOTES"')
    tables['BUILD'] = pd.DataFrame({'COMMAND': cmd})

    with pd.ExcelWriter(path, engine=XL_ENGINE) as xw:
        for name, df in tables.items():
            df.to_excel(xw, sheet_name=name, index=False)
            ws = xw.sheets[name]
            for i, c in enumerate(df.columns, 1):
                width = max([len(str(c))] + [len(fmt(v)) for v in df[c].head(500)]) + 2
                ws.column_dimensions[ws.cell(1, i).column_letter].width = min(width, 80)
    print(f'workbook written to {path}')
    return ' '.join(cmd)


# ---------------------------------------------------------------------- update
class _OpenpyxlBook:
    """No Excel needed; keeps VBA but drops charts/images and does not recalculate formulas."""

    def __init__(self, path):
        import openpyxl
        vba = path.lower().endswith('.xlsm')
        self.wb = openpyxl.load_workbook(path, keep_vba=vba)                    # formulas, written back
        self.cached = openpyxl.load_workbook(path, keep_vba=vba, data_only=True)  # last values Excel computed

    def sheets(self):
        return self.wb.sheetnames

    def read(self, sheet):
        return [list(r) for r in self.cached[sheet].iter_rows(values_only=True)]

    def formulas(self, sheet):
        return [[isinstance(v, str) and v.startswith('=') for v in r]
                for r in self.wb[sheet].iter_rows(values_only=True)]

    def write(self, sheet, row, col, value):
        self.wb[sheet].cell(row, col, value)

    def write_table(self, sheet, df):
        if sheet in self.wb.sheetnames:
            self.wb.remove(self.wb[sheet])
        ws = self.wb.create_sheet(sheet)
        ws.append([str(c) for c in df.columns])
        for row in df.itertuples(index=False):
            ws.append([None if fmt(v) == '' else (v.item() if hasattr(v, 'item') else v) for v in row])

    def save(self, path):
        self.wb.save(path)

    def close(self):
        pass


class _XlwingsBook:
    """Drives Excel itself: everything in the workbook is preserved and recalculated."""

    def __init__(self, path):
        import xlwings as xw
        self.app = xw.App(visible=False, add_book=False)
        self.wb = self.app.books.open(os.path.abspath(path))

    def sheets(self):
        return [s.name for s in self.wb.sheets]

    def read(self, sheet):
        return self._grid(self.wb.sheets[sheet].used_range.value)

    def formulas(self, sheet):
        return [[isinstance(v, str) and v.startswith('=') for v in r]
                for r in self._grid(self.wb.sheets[sheet].used_range.formula)]

    @staticmethod
    def _grid(v):
        return v if v and isinstance(v[0], list) else [v or []]

    def write(self, sheet, row, col, value):
        self.wb.sheets[sheet].range((row, col)).value = value

    def write_table(self, sheet, df):
        names = [s.name for s in self.wb.sheets]
        ws = self.wb.sheets[sheet] if sheet in names else self.wb.sheets.add(sheet, after=self.wb.sheets[-1])
        ws.clear()
        rows = [[str(c) for c in df.columns]]
        rows += [[None if fmt(v) == '' else (v.item() if hasattr(v, 'item') else v) for v in r]
                 for r in df.itertuples(index=False)]
        ws.range('A1').value = rows

    def save(self, path):
        self.wb.save(os.path.abspath(path))

    def close(self):
        self.wb.close()
        self.app.quit()


def _open(path, backend):
    if backend is None:
        try:
            import xlwings  # noqa: F401
            backend = 'xlwings'
        except ImportError:
            backend = 'openpyxl'
    return {'xlwings': _XlwingsBook, 'openpyxl': _OpenpyxlBook}[backend](path), backend


def _update_sheet(book, sheet, key, values, create=(), overwrite_formulas=False):
    """Write `values` (DataFrame indexed by lower-case key) into `sheet`, matched on column `key`.

    Columns of `values` missing from the sheet are created only if listed in `create`.
    Cells holding a formula are left alone unless `overwrite_formulas`.
    Returns (rows updated, formula cells skipped).
    """
    rows = book.read(sheet)
    if not rows:
        return 0, 0
    header = [str(c).strip().upper() if c is not None else '' for c in rows[0]]
    if key not in header:
        return 0, 0
    kcol = header.index(key)
    formulas = book.formulas(sheet)

    def is_formula(r, c):
        return r < len(formulas) and c < len(formulas[r]) and formulas[r][c]

    matched = [(i, fmt(r[kcol] if kcol < len(r) else None).lower()) for i, r in enumerate(rows[1:], 2)]
    matched = [(i, name) for i, name in matched if name in values.index]
    if not matched:
        return 0, 0
    cols = {}
    for c in values.columns:
        if c in header:
            cols[c] = header.index(c) + 1
        elif c in create:
            header.append(c)
            cols[c] = len(header)
            book.write(sheet, 1, cols[c], c)
    hits = skipped = 0
    for i, name in matched:
        hits += 1
        for c, col in cols.items():
            if not overwrite_formulas and is_formula(i - 1, col - 1):
                skipped += 1
                continue
            v = values.at[name, c]
            book.write(sheet, i, col, None if fmt(v) == '' else (v.item() if hasattr(v, 'item') else v))
    return hits, skipped


def _sheet_selected(name, patterns):
    return not patterns or any(fnmatch.fnmatch(name.lower(), p.lower()) for p in patterns)


def update_workbook(path, par=None, obs=None, res=None, obs_csv=None, real=None, pst=None,
                    out=None, backend=None, par_cols=('PARVAL1',), obs_cols=('OBSVAL', 'WEIGHT'),
                    overwrite_formulas=False, sheets=None, groups=None, phi=True):
    """Update an existing workbook in place (or to `out`).

    par: a Pst, a DataFrame with PARNME, a .par file or an IES case.N.par.csv (realization `real`)
                                                              -> `par_cols` on every sheet with a PARNME column
    obs: a Pst or a DataFrame with OBSNME                     -> `obs_cols` on every sheet with an OBSNME column
    res: a .res/.rei file path                                 -> MODELLED / RESIDUAL columns on those sheets
    obs_csv: an IES case.N.obs.csv (realization `real`)        -> MODELLED, plus RESIDUAL when `pst` is given
    sheets: glob patterns (case-insensitive); only matching worksheets are touched
    groups: parameter / observation group names; only rows in those groups are written
            (a .par file carries no groups: pass a DataFrame or Pst with PARGP instead)
    Cells that hold formulas are skipped unless `overwrite_formulas`.
    phi: with residuals (res, or obs_csv + pst) also write a PHI sheet with the objective function
         by observation group, and PHI_IES with the realization phis of an ensemble when
         case.phi.actual.csv is beside it.
    """
    groups = {g.strip().lower() for g in groups} if groups else None

    def frame(src, key, group_col, cols):
        if src is None:
            return None
        if isinstance(src, Pst):
            src = src.par if key == 'PARNME' else src.obs
        elif isinstance(src, str):
            src = read_par(src, real).reset_index()
        df = src.copy()
        df.columns = [str(c).upper() for c in df.columns]
        df[key] = df[key].astype(str).str.strip().str.lower()
        if groups:
            if group_col not in df:
                raise ValueError(f'groups requested but {key} rows carry no {group_col} column')
            df = df[df[group_col].astype(str).str.strip().str.lower().isin(groups)]
        return df.set_index(key)[[c for c in cols if c in df]]

    par_df = frame(par, 'PARNME', 'PARGP', par_cols)
    obs_df = frame(obs, 'OBSNME', 'OBGNME', obs_cols)
    res_df = residuals = None
    if res is not None and obs_csv is not None:
        raise ValueError('give res or obs_csv, not both')
    if res is not None:
        residuals = read_res(res)
    elif obs_csv is not None:
        residuals = read_obs_ensemble(obs_csv, real, pst)
    if residuals is not None:
        res_df = frame(residuals.reset_index(), 'NAME', 'GROUP', ('MODELLED', 'RESIDUAL'))
    phi_tables = {}
    if phi and residuals is not None and {'GROUP', 'RESIDUAL', 'WEIGHT'} <= set(residuals.columns):
        phi_tables['PHI'] = phi_by_group(residuals)
        if obs_csv is not None:
            reals = ies_phi(obs_csv)
            if reals is not None:
                phi_tables['PHI_IES'] = reals
    if par_df is None and obs_df is None and res_df is None:
        raise ValueError('nothing to update: give par, obs, res or obs_csv')

    book, backend = _open(path, backend)
    if backend == 'openpyxl':
        warnings.warn('openpyxl backend: macros are kept, but charts/images are dropped and '
                      'formulas are not recalculated until Excel opens the file')
    touched = {}
    try:
        for sheet in book.sheets():
            if not _sheet_selected(sheet, sheets):
                continue
            n = k = 0
            for key, df, create in (('PARNME', par_df, ()), ('OBSNME', obs_df, ()),
                                    ('OBSNME', res_df, ('MODELLED', 'RESIDUAL'))):
                if df is not None:
                    hits, skipped = _update_sheet(book, sheet, key, df, create, overwrite_formulas)
                    n, k = n + hits, k + skipped
            if n:
                print(f'{sheet}: {n} rows matched' + (f', {k} formula cells left alone' if k else ''))
                touched[sheet] = {'rows': n, 'formula_cells_skipped': k}
        for name, table in phi_tables.items():
            book.write_table(name, table)
            print(f'{name}: {len(table)} rows written')
            touched[name] = {'rows': len(table), 'formula_cells_skipped': 0}
        book.save(out or path)
    finally:
        book.close()
    print(f'workbook saved to {out or path} ({backend})')
    return {'sheets': touched, 'backend': backend}
