"""Objective-function summaries from residuals: what PEST prints at the end of a run, as a table.

phi_by_group() takes any table with GROUP, RESIDUAL and WEIGHT columns (a .res / .rei, or an
IES observation ensemble joined with the control file) and gives per-group contributions;
ies_phi() reads the realization phis PESTPP-IES records in case.phi.actual.csv.
"""
import os
import re

import numpy as np
import pandas as pd

PHI_COLUMNS = ['GROUP', 'N_OBS', 'N_WEIGHTED', 'PHI', 'PHI_FRACTION', 'RMS_RESIDUAL', 'MEAN_RESIDUAL',
               'MAX_ABS_RESIDUAL', 'WORST_OBS']


def phi_by_group(res):
    """Per-group objective function from a residuals table (GROUP, RESIDUAL, WEIGHT; index = name).

    PHI is sum((weight * residual)^2); residual statistics use weighted observations only,
    unweighted (they describe misfit in the observation's units). A TOTAL row closes the table.
    """
    df = pd.DataFrame({
        'GROUP': res['GROUP'].astype(str).str.lower(),
        'RESIDUAL': pd.to_numeric(res['RESIDUAL'], errors='coerce'),
        'WEIGHT': pd.to_numeric(res['WEIGHT'], errors='coerce').fillna(0),
    }, index=res.index)
    df['WR2'] = (df['WEIGHT'] * df['RESIDUAL']) ** 2
    rows = []
    for g, part in df.groupby('GROUP', sort=False):
        w = part[part['WEIGHT'] > 0]
        worst = w['RESIDUAL'].abs().idxmax() if len(w) else ''
        rows.append((g, len(part), len(w), w['WR2'].sum(),
                     np.nan,
                     np.sqrt((w['RESIDUAL'] ** 2).mean()) if len(w) else np.nan,
                     w['RESIDUAL'].mean() if len(w) else np.nan,
                     w['RESIDUAL'].abs().max() if len(w) else np.nan,
                     worst))
    out = pd.DataFrame(rows, columns=PHI_COLUMNS)
    total = out['PHI'].sum()
    out['PHI_FRACTION'] = out['PHI'] / total if total else np.nan
    w = df[df['WEIGHT'] > 0]
    out.loc[len(out)] = ('TOTAL', len(df), len(w), total, 1.0 if total else np.nan,
                         np.sqrt((w['RESIDUAL'] ** 2).mean()) if len(w) else np.nan,
                         w['RESIDUAL'].mean() if len(w) else np.nan,
                         w['RESIDUAL'].abs().max() if len(w) else np.nan,
                         w['RESIDUAL'].abs().idxmax() if len(w) else '')
    return out


def residuals_from_ensemble(modelled, pst):
    """RESIDUAL / WEIGHT / GROUP for an IES realization's simulated values against a Pst."""
    obs = pst.obs.set_index('OBSNME')
    df = pd.DataFrame({'MODELLED': pd.to_numeric(modelled)}, index=modelled.index)
    df['RESIDUAL'] = pd.to_numeric(obs['OBSVAL']).reindex(df.index) - df['MODELLED']
    df['WEIGHT'] = pd.to_numeric(obs['WEIGHT']).reindex(df.index)
    df['GROUP'] = obs['OBGNME'].reindex(df.index)
    return df.dropna(subset=['GROUP'])


_ENSEMBLE_NAME = re.compile(r'^(?P<case>.+?)\.(?P<iter>\d+)\.(par|obs)\.csv$', re.I)
_STATS = ('iteration', 'total_runs', 'mean', 'standard_deviation', 'min', 'max')


def ies_phi(ensemble_path):
    """Realization phis for the iteration of an IES ensemble file, from case.phi.actual.csv beside it.

    Returns a DataFrame (REALIZATION, PHI) sorted by phi, with MEAN / STD / MIN / MAX rows on
    top; None when the phi file or the iteration is not there.
    """
    m = _ENSEMBLE_NAME.match(os.path.basename(ensemble_path))
    if not m:
        return None
    phi_file = os.path.join(os.path.dirname(ensemble_path), f"{m['case']}.phi.actual.csv")
    if not os.path.exists(phi_file):
        return None
    phi = pd.read_csv(phi_file)
    phi.columns = [str(c).strip().lower() for c in phi.columns]
    row = phi[phi['iteration'] == int(m['iter'])]
    if row.empty:
        return None
    row = row.iloc[0]
    reals = pd.to_numeric(row.drop(labels=[c for c in phi.columns if c in _STATS])).sort_values()
    head = pd.DataFrame({'REALIZATION': ['MEAN', 'STD', 'MIN', 'MAX'],
                         'PHI': [row.get('mean'), row.get('standard_deviation'), row.get('min'), row.get('max')]})
    body = pd.DataFrame({'REALIZATION': reals.index.astype(str), 'PHI': reals.values})
    out = pd.concat([head, body], ignore_index=True)
    out.attrs['iteration'] = int(m['iter'])
    return out
