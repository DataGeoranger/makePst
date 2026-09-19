"""Pst -> PEST control file text (classic, or PEST++ version 2 with external csv tables)."""
import os

import pandas as pd

from .pst import OBS_COLS, PAR_COLS, PRIOR_COLS, Pst, table_lines
from .sections import AUI, COMPUTED, CONTROL, LSQR, REGUL, SVD, SVDA, fmt


def _block(header, lines):
    return header + '\n' + '\n'.join(lines) + '\n'


def _observation_groups(pst):
    return [f'{g} {pst.obs_cov[g]}' if g in pst.obs_cov else g for g in pst.obsgp]


def to_text(pst: Pst, validate=True):
    """Classic (version 1) control file text."""
    if validate:
        pst.validate()
    ctl = dict(pst.control)
    ctl.update(pst.counts)

    out = 'pcf\n'
    out += ''.join(f'# {c}\n' for c in pst.comments)
    out += CONTROL.render(ctl)
    if pst.use_svd:
        out += SVD.render(ctl)
    if 'lsqrmode' in ctl:
        out += LSQR.render(ctl)
    if str(ctl.get('doaui', '')).lower() == 'aui':
        aui = dict(ctl)
        aui.setdefault('maxaui', int((pst.par['PARTRANS'].isin(('log', 'none'))).sum()))
        out += AUI.render(aui)
    if 'basepestfile' in ctl:
        out += SVDA.render(ctl)
    if 'sensitivity reuse' in pst.raw_sections:
        out += _block('* sensitivity reuse', pst.raw_sections['sensitivity reuse'])

    out += _block('* parameter groups', table_lines(pst.pargp))

    par = pst.par
    out += _block('* parameter data', table_lines(par[PAR_COLS]))
    tied = par['PARTRANS'] == 'tied'
    if tied.any():
        out += '\n'.join(table_lines(par.loc[tied, ['PARNME', 'TIETO']])) + '\n'

    out += _block('* observation groups', _observation_groups(pst))
    out += _block('* observation data', table_lines(pst.obs[OBS_COLS]))
    if 'derivatives command line' in pst.raw_sections:
        out += _block('* derivatives command line', pst.raw_sections['derivatives command line'])
    out += _block('* model command line', pst.cmd)
    io = pd.DataFrame(pst.tpl + pst.ins, columns=['pest', 'model'])
    out += _block('* model input/output', table_lines(io))

    if pst.nprior:
        out += _block('* prior information', table_lines(pst.prior[PRIOR_COLS]))
    if 'predictive analysis' in pst.raw_sections:
        out += _block('* predictive analysis', pst.raw_sections['predictive analysis'])
    if pst.pestmode == 'regularisation':
        out += REGUL.render(ctl)
    if 'pareto' in pst.raw_sections:
        out += _block('* pareto', pst.raw_sections['pareto'])
    out += ''.join(f'++{k}({v})\n' for k, v in pst.pestpp)
    return out


# ---------------------------------------------------------------------- version 2
def effective_control(pst):
    """Every control value the classic writer would emit, as keyword -> value (counts excluded)."""
    ctl = dict(pst.control)
    out = {'pestmode': pst.pestmode}
    out.update(CONTROL.values(ctl))
    if pst.use_svd:
        out.update(SVD.values(ctl))
    if 'lsqrmode' in ctl:
        out.update(LSQR.values(ctl))
    if str(ctl.get('doaui', '')).lower() == 'aui':
        out.update(AUI.values(ctl))
    if 'basepestfile' in ctl:
        out.update(SVDA.values(ctl))
    if pst.pestmode == 'regularisation':
        out.update(REGUL.values(ctl))
    return {k: v for k, v in out.items() if (k not in COMPUTED or k == 'pestmode') and fmt(v) != ''}


def external_tables(pst: Pst, stem):
    """The csv tables a version-2 file points at: {file name: DataFrame} with PEST++ column names."""
    par = pst.par[PAR_COLS].copy()
    if (pst.par['PARTRANS'] == 'tied').any():
        par['partied'] = pst.par['TIETO'].where(pst.par['PARTRANS'] == 'tied', '')
    tables = {
        f'{stem}.pargp_data.csv': pst.pargp.rename(columns=str.lower),
        f'{stem}.par_data.csv': par.rename(columns=str.lower),
        f'{stem}.obs_data.csv': pst.obs[OBS_COLS].rename(columns=str.lower),
    }
    if pst.nprior:
        prior = pst.prior[PRIOR_COLS].rename(columns={'PINME': 'pilbl', 'EQ': 'equation',
                                                      'WEIGHT': 'weight', 'OBGNME': 'obgnme'})
        tables[f'{stem}.prior_data.csv'] = prior
    return tables


def to_text_v2(pst: Pst, stem, validate=True):
    """PEST++ version-2 text; the tables it references come from external_tables(pst, stem)."""
    if validate:
        pst.validate()
    out = 'pcf version=2\n'
    out += ''.join(f'# {c}\n' for c in pst.comments)
    out += '* control data keyword\n'
    for k, v in effective_control(pst).items():
        out += f'{k:<22}{fmt(v)}\n'
    for name in ('sensitivity reuse',):
        if name in pst.raw_sections:
            out += _block(f'* {name}', pst.raw_sections[name])
    out += f'* parameter groups external\n{stem}.pargp_data.csv\n'
    out += f'* parameter data external\n{stem}.par_data.csv\n'
    out += _block('* observation groups', _observation_groups(pst))
    out += f'* observation data external\n{stem}.obs_data.csv\n'
    if 'derivatives command line' in pst.raw_sections:
        out += _block('* derivatives command line', pst.raw_sections['derivatives command line'])
    out += _block('* model command line', pst.cmd)
    io = pd.DataFrame(pst.tpl + pst.ins, columns=['pest', 'model'])
    out += _block('* model input/output', table_lines(io))
    if pst.nprior:
        out += f'* prior information external\n{stem}.prior_data.csv\n'
    for name in ('predictive analysis', 'pareto'):
        if name in pst.raw_sections:
            out += _block(f'* {name}', pst.raw_sections[name])
    out += ''.join(f'++{k}({v})\n' for k, v in pst.pestpp)
    return out


def write_pst(pst: Pst, path, dump_tpl=True, version=None):
    """Write `pst` to `path`; version 1 (classic) or 2 (PEST++ external tables beside the file).

    `version=None` keeps the version the Pst was read with (1 for a Pst built from tables).
    Returns the list of files written.
    """
    version = version or getattr(pst, 'version', 1)
    folder = os.path.dirname(path) or '.'
    written = [path]
    if version == 2:
        stem = os.path.splitext(os.path.basename(path))[0]
        text = to_text_v2(pst, stem)
        for name, df in external_tables(pst, stem).items():
            df.to_csv(os.path.join(folder, name), index=False, lineterminator='\n')
            written.append(os.path.join(folder, name))
    else:
        text = to_text(pst)
    with open(path, 'w', newline='') as f:
        f.write(text)
    if dump_tpl:
        write_dump_tpl(pst, os.path.join(folder, 'dump.tpl'))
    print(f'pst written to {path}' + (f' (version 2, {len(written) - 1} csv tables)' if version == 2 else ''))
    return written


def write_dump_tpl(pst: Pst, path):
    """A template file that echoes every parameter; handy for checking what PEST sends."""
    par = pd.DataFrame({'name': pst.par['PARNME'], 'tpl': '~       ' + pst.par['PARNME'] + '       ~'})
    with open(path, 'w', newline='') as f:
        f.write('ptf ~\n' + '\n'.join(table_lines(par)) + '\n')
