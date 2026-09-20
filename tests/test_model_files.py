"""TEMPCHEK / INSCHEK in Python: the number writer, template filling, .obf files and the two commands."""
import os
import shutil
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from makepst.checks import instruction_problems, validate as run_checks  # noqa: E402
from makepst.cli import main  # noqa: E402
from makepst.model_files import FieldError, fill_template, read_obf, scaled_values, write_number  # noqa: E402
from makepst.reader import read_pst  # noqa: E402

MINIMAL = os.path.join(ROOT, 'examples', 'minimal')


# ---------------------------------------------------------------------- write_number
@pytest.mark.parametrize('value, width, precis, dpoint, expected', [
    (12.5, 10, 'single', 'point', '12.5'),
    (1234567.89, 8, 'single', 'point', '1234568.'),          # fixed beats 1.2346E6
    (0.000123456, 8, 'single', 'point', '.0001235'),         # Fortran drops the optional zero
    (0.000123456, 8, 'single', 'nopoint', '12346E-8'),       # one more digit without the point
    (-0.5, 3, 'single', 'point', '-.5'),
    (0.0, 2, 'single', 'point', '0.'),
    (0.0, 1, 'single', 'nopoint', '0'),
    (0.001, 5, 'single', 'point', '0.001'),
    (0.001, 5, 'single', 'nopoint', '1E-3'),
    (2.5e-7, 6, 'single', 'point', '2.5E-7'),
    (1e10, 5, 'single', 'point', '1.E10'),
    (123456789012, 8, 'single', 'nopoint', '123457E6'),
    (98765.4321, 13, 'single', 'point', '98765.432'),        # single: 8 significant digits
    (98765.4321, 13, 'double', 'point', '98765.4321'),
    (3.14159265358979, 23, 'double', 'point', '3.14159265358979'),
    (100, 3, 'single', 'nopoint', '100'),
])
def test_write_number(value, width, precis, dpoint, expected):
    assert write_number(value, width, precis, dpoint) == expected


def test_write_number_always_fits_and_keeps_the_leading_digits():
    values = [0.0, 1.0, -1.0, 12.5, 1 / 3, 2 / 3, 1e-4, 12345.678, -98765.4321, 1e-9, 6.02e23, -273.15]
    for v in values:
        for w in range(3, 24):
            for precis in ('single', 'double'):
                for dpoint in ('point', 'nopoint'):
                    try:
                        s = write_number(v, w, precis, dpoint)
                    except FieldError:
                        continue
                    assert len(s) <= w, (v, w, s)
                    got = float(s)
                    if v != 0:
                        assert abs(got - v) / abs(v) < 0.5, (v, w, s)     # at least the leading digit
                        if w >= 8:
                            assert abs(got - v) / abs(v) < 1e-3, (v, w, s)
                    if dpoint == 'point':
                        assert '.' in s


def test_write_number_errors():
    with pytest.raises(FieldError, match='too small'):
        write_number(100, 3)                            # 100. needs four characters with the point
    with pytest.raises(FieldError, match='too small'):
        write_number(1e-5, 4)
    with pytest.raises(FieldError, match='single precision'):
        write_number(1e40, 12)
    assert write_number(1e40, 12, 'double') == '1.E40'
    with pytest.raises(FieldError, match='double precision'):
        write_number(1e280, 12, 'double')


# ---------------------------------------------------------------------- templates
def test_fill_template_right_justifies_one_word_per_parameter(tmp_path):
    tpl = tmp_path / 'a.tpl'
    tpl.write_text('ptf ~\nk = ~   k1   ~ and ~ k1 ~ again ~k2 ~\n')
    text, problems = fill_template(tpl, {'k1': 1234.5678, 'k2': -2})
    assert problems == []
    # k1's narrowest space is 6 characters wide: the same word, sized for it, right-justified in both
    assert text == 'k =     1234.6 and 1234.6 again   -2.\n'


def test_fill_template_one_word_sized_for_the_narrowest_space(tmp_path):
    tpl = tmp_path / 'a.tpl'
    tpl.write_text('ptf ~\n~   k1   ~ ~k1~\n')
    text, problems = fill_template(tpl, {'k1': 1234.5678})
    assert problems == [] and text == '      1.E3 1.E3\n'          # 4 characters: only the exponent form fits


def test_fill_template_problems(tmp_path):
    tpl = tmp_path / 'a.tpl'
    tpl.write_text('ptf ~\n~k1~ ~ k2 ~ ~k3~\n')
    text, problems = fill_template(tpl, {'k1': 1e-12, 'k2': 5})
    assert text is None
    assert any('"k1" (1e-12 in 4 characters): field width too small' in p for p in problems)
    assert any('"k3" cited in the template has no value' in p for p in problems)
    from makepst.model_files import fit_problems
    assert len(fit_problems(tpl, {'k1': 1e-12, 'k2': 5})) == 1       # missing names are not its business


def test_scaled_values_applies_scale_and_offset():
    p = read_pst(os.path.join(HERE, 'data', 'demo.pst'))
    p.par.loc[0, 'SCALE'], p.par.loc[0, 'OFFSET'] = 2.0, 1.0
    v = scaled_values(p.par)
    assert v[p.par.loc[0, 'PARNME']] == pytest.approx(2 * float(p.par.loc[0, 'PARVAL1']) + 1)


def test_validate_reports_values_that_do_not_fit(tmp_path):
    shutil.copytree(MINIMAL, tmp_path / 'm')
    (tmp_path / 'm' / 'model.tpl').write_text('ptf ~\nhk1  ~hk1~\nhk2  ~ hk2 ~\nhk3  ~ hk3 ~\nrch  ~rch~\n')
    par = (tmp_path / 'm' / 'par.csv').read_text().replace('rch,none,relative,0.001,', 'rch,none,relative,1e-10,')
    (tmp_path / 'm' / 'par.csv').write_text(par)
    os.chdir(tmp_path / 'm')
    main(['build', 'model.pst', 'regul', '--set_ctl_csv', 'control.csv', '--add_pargp_csv', 'pargp.csv',
          '--add_par_csv', 'par.csv', '--add_obs_csv', 'obs.csv', '--add_io_csv', 'io.csv', '--no_manifest'])
    findings = run_checks(read_pst('model.pst'), base_dir='.')
    msgs = [f.message for f in findings if f.severity == 'error']
    assert any('value cannot be written into its space: parameter "rch" (1e-10 in 5 characters)' in m for m in msgs)
    assert not any('"hk1"' in m for m in msgs)                       # 10. fits in 5


# ---------------------------------------------------------------------- inschek's ordering rules
def test_instruction_ordering_rules(tmp_path):
    ins = tmp_path / 'a.ins'
    ins.write_text('pif @\nl1 !a! l2 !b!\nl1 t20 !c! t10 !d!\nl1 [e]10:15 [f]5:8\n& l3 !g!\nl1 t5 [h]10:12 t12 (i)12:20\n')
    joined = '\n'.join(instruction_problems(ins))
    assert 'line 2: a line advance (l2) can only occur at the beginning' in joined
    assert 'line 3: t10 moves backwards' in joined
    assert 'line 4: [f]5:8 starts left of column 15' in joined
    assert 'line 5: a line advance (l3) can only occur at the beginning' in joined
    assert 'line 6' not in joined


# ---------------------------------------------------------------------- commands
@pytest.fixture
def case(tmp_path, monkeypatch):
    shutil.copytree(MINIMAL, tmp_path / 'm')
    monkeypatch.chdir(tmp_path / 'm')
    main(['build', 'model.pst', 'regul', '--set_ctl_csv', 'control.csv', '--add_pargp_csv', 'pargp.csv',
          '--add_par_csv', 'par.csv', '--add_obs_csv', 'obs.csv', '--add_io_csv', 'io.csv', '--no_manifest',
          '--no_dump_tpl'])
    return tmp_path / 'm'


def test_tempchek_template_only(case, capsys):
    main(['tempchek', 'model.tpl'])
    out = capsys.readouterr().out
    assert '4 parameters identified in model.tpl: hk1 hk2 hk3 rch' in out and '0 errors' in out


def test_tempchek_writes_model_input(case, capsys):
    main(['tempchek', 'model.tpl', 'new.in', 'model.par'])
    assert (case / 'new.in').read_text() == 'hk1     12.5\nhk2      18.\nhk3     12.5\nrch   0.0012\n'
    main(['tempchek', 'model.tpl', 'new2.in'])                       # parfile defaults to model.par
    assert (case / 'new2.in').read_text() == (case / 'new.in').read_text()


def test_tempchek_reports_unwritable_values(case, capsys):
    (case / 'narrow.tpl').write_text('ptf ~\nk ~k~ ~x~\n')
    (case / 'narrow.par').write_text('single point\nk 12345.6 1 0\ny 1 1 0\n')
    with pytest.raises(SystemExit):
        main(['tempchek', 'narrow.tpl', 'narrow.in'])
    out = capsys.readouterr().out
    assert 'parameter "k" (12345.6 in 3 characters): field width too small' in out
    assert 'parameter "x" cited in the template has no value' in out
    assert 'WARNING parameter "y" from narrow.par not cited in narrow.tpl' in out
    assert not (case / 'narrow.in').exists()


def test_tempchek_case(case, capsys):
    main(['tempchek', 'model.pst', '--dry_run'])
    assert 'model.in can be written' in capsys.readouterr().out
    before = (case / 'model.in').read_text()
    main(['tempchek', 'model.pst'])                                  # PARVAL1 from the control file
    assert (case / 'model.in').read_text() == 'hk1      10.\nhk2      20.\nhk3      10.\nrch    0.001\n' != before
    main(['tempchek', 'model.pst', '--par', 'model.par'])
    assert (case / 'model.in').read_text() == 'hk1     12.5\nhk2      18.\nhk3     12.5\nrch   0.0012\n'


def test_inschek_instruction_only(case, capsys):
    main(['inschek', 'heads.ins'])
    assert '3 observations identified in heads.ins: h_w1 h_w2 h_w3' in capsys.readouterr().out
    (case / 'bad.ins').write_text('pif @\nw !x!\n')
    with pytest.raises(SystemExit):
        main(['inschek', 'bad.ins'])
    assert 'must begin with "l", a marker or "&"' in capsys.readouterr().out


def test_inschek_writes_obf(case, capsys):
    main(['inschek', 'heads.ins', 'heads.out'])
    assert read_obf(case / 'heads.obf') == {'h_w1': 101.5, 'h_w2': 98.5, 'h_w3': 94.8}
    main(['inschek', 'model.pst'])
    assert read_obf(case / 'model.obf') == {'h_w1': 101.5, 'h_w2': 98.5, 'h_w3': 94.8, 'q_gauge': 1001.0}
    out = capsys.readouterr().out
    assert 'read    3 observations from heads.out with heads.ins' in out and 'written model.obf: 4' in out


def test_inschek_case_reports_missing_output(case, capsys):
    os.remove(case / 'flow.out')
    with pytest.raises(SystemExit):
        main(['inschek', 'model.pst'])
    out = capsys.readouterr().out
    assert 'ERROR   flow.ins: model output file flow.out not found' in out
    assert 'WARNING 1 observations in the control file were not read: q_gauge' in out
    assert read_obf(case / 'model.obf') == {'h_w1': 101.5, 'h_w2': 98.5, 'h_w3': 94.8}
