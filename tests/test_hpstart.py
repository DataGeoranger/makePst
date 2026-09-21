"""PEST_HP accelerator file updates preserve instruction metadata."""
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from makepst.cli import main  # noqa: E402
from makepst.hpstart import write_hpstart  # noqa: E402
from makepst.reader import read_pst  # noqa: E402
from make_fixture import DATA, PST  # noqa: E402


def template(path, npar, nobs):
    metadata = (np.arange(3 * nobs + 2, dtype='<i4') + 1).tobytes()
    raw = (np.array([npar, nobs, 2], dtype='<i4').tobytes()
           + np.ones(npar, dtype='<f8').tobytes()
           + np.zeros(nobs, dtype='<f8').tobytes() + metadata)
    path.write_bytes(raw)
    return raw


def test_res_updates_only_reference_observations(tmp_path):
    pst = read_pst(PST)
    source = template(tmp_path / 'source.hp', pst.npar, pst.nobs)
    out = tmp_path / 'start.hp'
    main(['hpstart', PST, str(out), '--template', str(tmp_path / 'source.hp'),
          '--res', os.path.join(DATA, 'demo.res'), '--no_manifest'])
    result = out.read_bytes()
    start = 12 + 8 * pst.npar
    stop = start + 8 * pst.nobs
    assert result[:start] == source[:start]
    assert result[stop:] == source[stop:]
    modeled = np.frombuffer(result[start:stop], dtype='<f8')
    assert len(modeled) == pst.nobs
    assert modeled[0] == pytest.approx(2543.59)


def test_ies_realization_and_parameter_values(tmp_path):
    pst = read_pst(PST)
    source = tmp_path / 'source.hp'
    template(source, pst.npar, pst.nobs)
    out = tmp_path / 'start.hp'
    write_hpstart(pst, source, out, obs_csv=os.path.join(DATA, 'demo.3.obs.csv'),
                  real='1', par=os.path.join(DATA, 'demo.3.par.csv'))
    raw = out.read_bytes()
    pvals = np.frombuffer(raw, dtype='<f8', count=pst.npar, offset=12)
    modeled = np.frombuffer(raw, dtype='<f8', count=pst.nobs, offset=12 + 8 * pst.npar)
    assert modeled[0] == pytest.approx(2543.09)
    assert pvals[0] != 1.0


def test_rejects_incompatible_template_and_missing_values(tmp_path):
    pst = read_pst(PST)
    source = tmp_path / 'source.hp'
    template(source, pst.npar, pst.nobs - 1)
    with pytest.raises(ValueError, match='counts'):
        write_hpstart(pst, source, tmp_path / 'bad.hp', res=os.path.join(DATA, 'demo.res'))
    template(source, pst.npar, pst.nobs)
    partial = tmp_path / 'partial.res'
    partial.write_text('Name Group Measured Modelled Residual Weight\n'
                       'mr1158636_197611 head 1 2 -1 1\n')
    with pytest.raises(ValueError, match='missing'):
        write_hpstart(pst, source, tmp_path / 'bad.hp', res=partial)
    assert not (tmp_path / 'bad.hp').exists()
