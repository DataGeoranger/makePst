"""The pyEMU bridge; skipped when pyemu is not installed (pip install makepst[pyemu])."""
import os
import sys
import warnings

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

pyemu = pytest.importorskip('pyemu')

from makepst import read_pst  # noqa: E402
from makepst.diff import compare  # noqa: E402
from makepst.pyemu_bridge import from_pyemu, to_pyemu  # noqa: E402
from make_fixture import PST  # noqa: E402


def test_to_pyemu_carries_the_tables():
    p = read_pst(PST)
    pp = to_pyemu(p)
    assert isinstance(pp, pyemu.Pst)
    assert (pp.npar, pp.nobs, pp.nprior) == (11, 6, 6)
    assert pp.control_data.pestmode == 'regularisation'
    assert pp.control_data.noptmax == 10 and pp.control_data.jacupdate == 999
    assert pp.parameter_data.loc['hk1_cc02', 'partrans'] == 'tied'
    assert pp.parameter_data.loc['hk1_cc02', 'partied'] == 'hk1_cc01'
    assert np.isclose(pp.parameter_data.loc['hk1_cc01', 'parval1'], 49.73775)
    assert np.isclose(pp.observation_data.loc['qbs_2010', 'obsval'], 1234567.891)
    assert pp.pestpp_options == {'overdue_resched_fac': '3', 'lambdas': '0.1,1,10,100', 'max_run_fail': '2'}
    assert pp.reg_data.phimlim == 5.0 and pp.svd_data.maxsing == 50


def test_round_trip_through_pyemu_keeps_tables_and_reports_the_rest():
    p = read_pst(PST)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        q = from_pyemu(to_pyemu(p))
    d = compare(p, q)
    # the tables come back intact ...
    assert d.par.empty and d.obs.empty and d.prior.empty and d.pestpp.empty and d.io.empty and d.cmd.empty
    assert d.pargp[d.pargp['column'].isin(['INCTYP', 'DERINC', 'FORCEN'])].empty      # only split-* defaults added
    # ... what pyEMU's model does not carry is exactly what the README says
    ctl = d.control.set_index('NAME')
    assert ctl.loc['absparmax', 'change'] == 'removed'          # PEST_HP absparmax(n)=
    assert ctl.loc['uptestmin', 'change'] == 'removed'          # PEST_HP keyed token
    assert set(d.comments['change']) == {'removed'}             # header comments
