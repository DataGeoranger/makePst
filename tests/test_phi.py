"""Objective-function summaries written by update --res / --obs_csv."""
import os
import shutil
import sys

import numpy as np
import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from makepst import read_pst, read_res, update_workbook  # noqa: E402
from makepst.cli import main  # noqa: E402
from makepst.phi import ies_phi, phi_by_group  # noqa: E402
from make_fixture import BOOK, DATA, PST  # noqa: E402

RES = os.path.join(DATA, 'demo.res')
OBS_CSV = os.path.join(DATA, 'demo.3.obs.csv')


def test_phi_by_group_from_res():
    t = phi_by_group(read_res(RES)).set_index('GROUP')
    # demo.res: every residual is -1; weights 0.15, 0.15, 0, 0 (head/headss), 1e-6 (qbs), 0.2 (lhss)
    assert list(t.index) == ['head', 'headss', 'qbs', 'lhss', 'TOTAL']
    assert t.loc['head', 'N_OBS'] == 2 and t.loc['head', 'N_WEIGHTED'] == 2
    assert t.loc['head', 'PHI'] == pytest.approx(2 * 0.15 ** 2)
    assert t.loc['headss', 'N_WEIGHTED'] == 0 and t.loc['headss', 'PHI'] == 0 and np.isnan(t.loc['headss', 'RMS_RESIDUAL'])
    assert t.loc['lhss', 'PHI'] == pytest.approx(0.2 ** 2)
    total = 2 * 0.15 ** 2 + (1e-6) ** 2 + 0.2 ** 2
    assert t.loc['TOTAL', 'PHI'] == pytest.approx(total) and t.loc['TOTAL', 'PHI_FRACTION'] == 1.0
    assert t.loc['head', 'PHI_FRACTION'] == pytest.approx(2 * 0.15 ** 2 / total)
    assert t.loc['TOTAL', 'RMS_RESIDUAL'] == pytest.approx(1.0) and t.loc['TOTAL', 'MEAN_RESIDUAL'] == pytest.approx(-1.0)
    assert t.loc['head', 'WORST_OBS'] in ('mr1158636_197611', 'mr1158636_197705')


def test_ies_phi_table():
    t = ies_phi(OBS_CSV)
    assert t.attrs['iteration'] == 3
    assert t['REALIZATION'].tolist()[:4] == ['MEAN', 'STD', 'MIN', 'MAX']
    assert t['REALIZATION'].tolist()[4:] == ['1', 'base', '0']            # sorted by phi: 2, 3, 5
    assert t['PHI'].tolist()[4:] == [2.0, 3.0, 5.0]
    assert ies_phi(os.path.join(DATA, 'demo.par')) is None                # not an ensemble name


def test_update_res_writes_phi_sheet(tmp_path):
    book = tmp_path / 'b.xlsx'
    shutil.copy(BOOK, book)
    update_workbook(str(book), res=RES, backend='openpyxl')
    phi = pd.read_excel(book, 'PHI').set_index('GROUP')
    assert phi.loc['TOTAL', 'N_OBS'] == 6 and phi.loc['head', 'PHI'] == pytest.approx(0.045)
    assert 'PHI_IES' not in pd.ExcelFile(book).sheet_names
    update_workbook(str(book), res=RES, backend='openpyxl')              # second run replaces, not appends
    assert len(pd.read_excel(book, 'PHI')) == 5
    update_workbook(str(book), res=RES, backend='openpyxl', phi=False)
    assert 'PHI' in pd.ExcelFile(book).sheet_names                        # left as it was, not removed


def test_update_obs_csv_writes_phi_and_realizations(tmp_path):
    book = tmp_path / 'b.xlsx'
    shutil.copy(BOOK, book)
    main(['update', str(book), '--obs_csv', OBS_CSV, '--pst', PST, '--real', 'base', '--backend', 'openpyxl',
          '--no_manifest'])
    phi = pd.read_excel(book, 'PHI').set_index('GROUP')
    # base realization: modelled = observed + 1 -> residual -1 everywhere, same numbers as the .res
    assert phi.loc['TOTAL', 'PHI'] == pytest.approx(2 * 0.15 ** 2 + 1e-12 + 0.2 ** 2)
    reals = pd.read_excel(book, 'PHI_IES')
    assert reals['REALIZATION'].astype(str).tolist()[4:] == ['1', 'base', '0']
    # without a pst there are no residuals, hence no PHI sheet
    book2 = tmp_path / 'c.xlsx'
    shutil.copy(BOOK, book2)
    main(['update', str(book2), '--obs_csv', OBS_CSV, '--backend', 'openpyxl', '--no_manifest'])
    assert 'PHI' not in pd.ExcelFile(book2).sheet_names
    main(['update', str(book2), '--res', RES, '--backend', 'openpyxl', '--no_manifest', '--no_phi'])
    assert 'PHI' not in pd.ExcelFile(book2).sheet_names
