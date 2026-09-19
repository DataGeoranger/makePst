"""PEST++ version-2 control files (external csv tables) and observation covariance references."""
import os
import sys

import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from makepst import from_text, read_pst, to_text, write_pst  # noqa: E402
from makepst.cli import main  # noqa: E402
from makepst.diff import compare  # noqa: E402
from make_fixture import BUILD_ARGS, PST  # noqa: E402


def test_write_v2_and_read_back(tmp_path):
    p = read_pst(PST)
    files = write_pst(p, str(tmp_path / 'demo.pst'), dump_tpl=False, version=2)
    names = sorted(os.path.basename(f) for f in files)
    assert names == ['demo.obs_data.csv', 'demo.par_data.csv', 'demo.pargp_data.csv', 'demo.prior_data.csv', 'demo.pst']
    text = (tmp_path / 'demo.pst').read_text()
    assert text.startswith('pcf version=2\n') and '* control data keyword' in text
    assert '* parameter data external\ndemo.par_data.csv' in text and '* prior information external' in text
    assert 'noptmax' in text and 'jacupdate' in text and 'win_mrun_hours' in text and 'phimlim' in text
    assert 'npar' not in text.split('* parameter groups external')[0]           # counts are not keywords
    par = pd.read_csv(tmp_path / 'demo.par_data.csv')
    assert list(par.columns) == ['parnme', 'partrans', 'parchglim', 'parval1', 'parlbnd', 'parubnd',
                                 'pargp', 'scale', 'offset', 'dercom', 'partied']
    assert par.set_index('parnme').loc['hk1_cc02', 'partied'] == 'hk1_cc01'
    assert par['partied'].isna().sum() == 10                                      # blank for untied

    q = read_pst(str(tmp_path / 'demo.pst'))
    assert q.version == 2
    assert compare(p, q).empty
    assert to_text(q) == to_text(p)                                              # classic text identical


def test_version_is_kept_by_default(tmp_path):
    p = read_pst(PST)
    write_pst(p, str(tmp_path / 'a.pst'), dump_tpl=False, version=2)
    q = read_pst(str(tmp_path / 'a.pst'))
    write_pst(q, str(tmp_path / 'b.pst'), dump_tpl=False)                        # no version given: stays 2
    assert (tmp_path / 'b.pst').read_text().startswith('pcf version=2')
    write_pst(q, str(tmp_path / 'c.pst'), dump_tpl=False, version=1)
    assert (tmp_path / 'c.pst').read_text().startswith('pcf\n')


def test_cli_v2_flags(tmp_path):
    out = tmp_path / 'v2.pst'
    args = list(BUILD_ARGS)
    args[0] = str(out)
    main(args + ['--v2', '--no_manifest'])
    assert out.read_text().startswith('pcf version=2') and (tmp_path / 'v2.obs_data.csv').exists()
    main(['parrep', str(out), os.path.join(HERE, 'data', 'demo.par'), str(tmp_path / 'rep.pst'), '--no_manifest'])
    assert (tmp_path / 'rep.pst').read_text().startswith('pcf version=2')      # input was v2
    main(['parrep', str(out), os.path.join(HERE, 'data', 'demo.par'), str(tmp_path / 'rep1.pst'), '--v1',
          '--no_manifest'])
    assert (tmp_path / 'rep1.pst').read_text().startswith('pcf\n')
    assert compare(read_pst(str(tmp_path / 'rep.pst')), read_pst(str(tmp_path / 'rep1.pst'))).empty


def test_read_handwritten_v2(tmp_path):
    (tmp_path / 'par.csv').write_text(
        'parnme,partrans,parchglim,parval1,parlbnd,parubnd,pargp,scale,offset,dercom,partied,extra\n'
        'K1,log,factor,10,1,100,hk,1,0,1,,ignored\n'
        'k2,tied,factor,10,1,100,hk,1,0,1,k1,ignored\n')
    (tmp_path / 'pargp.csv').write_text('pargpnme,inctyp,derinc,derinclb,forcen,derincmul,dermthd\n'
                                        'hk,relative,0.01,0,switch,2,parabolic\n')
    (tmp_path / 'obs.csv').write_text('obsnme,obsval,weight,obgnme\nH1,1.5,1,head\nh2,2.5,0,head\n')
    (tmp_path / 'io.csv').write_text('pest_file,model_file\nm.tpl,m.in\nh.ins,h.out\n')
    (tmp_path / 'm.tpl').write_text('ptf ~\n~k1~ ~k2~\n')
    (tmp_path / 'v2.pst').write_text(
        'pcf version=2\n# made by hand\n* control data keyword\n'
        'pestmode  estimation\nnoptmax   3\nlamforgive lamforgive\n'
        'ies_num_reals  50\n'                                     # a PEST++ option in the keyword section
        '* parameter groups external\npargp.csv\n'
        '* parameter data external\npar.csv\n'
        '* observation data external\nobs.csv\n'
        '* model command line\nrun.bat\n'
        '* model input/output external\nio.csv\n'
        '++svd_pack(redsvd)\n')
    p = read_pst(str(tmp_path / 'v2.pst'))
    assert p.version == 2 and p.comments == ['made by hand']
    assert p.control['noptmax'] == 3 and p.control['lamforgive'] == 'lamforgive'
    assert p.pestpp == [('ies_num_reals', '50'), ('svd_pack', 'redsvd')]
    assert list(p.par['PARNME']) == ['k1', 'k2'] and p.par.set_index('PARNME').loc['k2', 'TIETO'] == 'k1'
    assert list(p.obs['OBSNME']) == ['h1', 'h2'] and p.obsgp == ['head']
    assert p.tpl == [('m.tpl', 'm.in')] and p.ins == [('h.ins', 'h.out')]      # told apart by ptf line / extension
    text = to_text(p)
    assert '* parameter data\nk1' in text and 'k2  k1' in text and '++ies_num_reals(50)' in text


def test_v2_missing_table_is_an_error(tmp_path):
    (tmp_path / 'bad.pst').write_text('pcf version=2\n* control data keyword\nnoptmax 1\n'
                                      '* parameter data external\nnope.csv\n')
    with pytest.raises(FileNotFoundError, match='nope.csv'):
        read_pst(str(tmp_path / 'bad.pst'))


def test_observation_covariance_round_trip(tmp_path):
    text = open(PST).read().replace('* observation groups\nhead\nheadss', '* observation groups\nhead heads.cov\nheadss')
    p = from_text(text)
    assert p.obs_cov == {'head': 'heads.cov'}
    out = to_text(p)
    assert '* observation groups\nhead heads.cov\nheadss\n' in out
    assert from_text(out).obs_cov == {'head': 'heads.cov'}
    write_pst(p, str(tmp_path / 'cov.pst'), dump_tpl=False, version=2)
    assert read_pst(str(tmp_path / 'cov.pst')).obs_cov == {'head': 'heads.cov'}
    # dump -> OBSGP sheet -> build keeps it
    main(['dump', str(tmp_path / 'cov.pst'), str(tmp_path / 'cov.xlsx'), '--no_manifest'])
    sheet = pd.read_excel(tmp_path / 'cov.xlsx', 'OBSGP')
    assert sheet.set_index('OBGNME').loc['head', 'COVFILE'] == 'heads.cov'
    main(['build', str(tmp_path / 'cov.xlsx'), '--out', str(tmp_path / 'rebuilt.pst'), '--no_manifest', '--v1'])
    assert read_pst(str(tmp_path / 'rebuilt.pst')).obs_cov == {'head': 'heads.cov'}
