"""`makepst log` (the ledger of manifests) and `makepst bundle` (a run zipped for reproduction)."""
import os
import shutil
import sys
import zipfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from makepst.cli import main  # noqa: E402
from makepst.provenance import find_manifests, mentions  # noqa: E402

MINIMAL = os.path.join(ROOT, 'examples', 'minimal')


@pytest.fixture
def project(tmp_path, monkeypatch):
    """The tutorial run: build, dump, update, parrep, each leaving a manifest."""
    shutil.copytree(MINIMAL, tmp_path / 'm')
    monkeypatch.chdir(tmp_path / 'm')
    main(['build', 'model.pst', 'regul', '--set_ctl_csv', 'control.csv', '--add_pargp_csv', 'pargp.csv',
          '--add_par_csv', 'par.csv', '--add_obs_csv', 'obs.csv', '--add_io_csv', 'io.csv'])
    main(['dump', 'model.pst', 'model.xlsx'])
    main(['update', 'model.xlsx', '--par', 'model.par', '--res', 'model.res', '--out', 'model2.xlsx',
          '--backend', 'openpyxl'])
    main(['parrep', 'model.pst', 'model.par', 'final.pst', '--set', 'noptmax=0'])
    return tmp_path / 'm'


# ---------------------------------------------------------------------- log
def test_log_lists_every_manifest_in_order(project, capsys):
    main(['log'])
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert [ln.split()[2] for ln in lines] == ['build', 'dump', 'update', 'parrep']
    assert 'model.pst <- control.csv, pargp.csv, par.csv, obs.csv, io.csv  [4 par 4 obs 2 prior]' in lines[0]
    assert 'model2.xlsx <- model.xlsx, model.par, model.res  [11 rows in 3 sheets]' in lines[2]
    assert all('makepst ' in ln for ln in lines)


def test_log_filters(project, capsys):
    main(['log', '--file', 'model.par'])
    assert [ln.split()[2] for ln in capsys.readouterr().out.splitlines()] == ['update', 'parrep']
    main(['log', '--command', 'dump', '--command', 'build'])
    assert [ln.split()[2] for ln in capsys.readouterr().out.splitlines()] == ['build', 'dump']
    main(['log', '--last', '1'])
    assert [ln.split()[2] for ln in capsys.readouterr().out.splitlines()] == ['parrep']
    sha = find_manifests(['.'])[0]['output']['sha256']
    main(['log', '--file', sha[:12]])                    # a hash prefix finds the runs that used that file
    assert [ln.split()[2] for ln in capsys.readouterr().out.splitlines()] == ['build', 'dump', 'parrep']
    main(['log', '--file', 'absent.xlsx'])
    assert 'no manifests found' in capsys.readouterr().out


def test_log_check_reports_changed_files(project, capsys):
    (project / 'model.par').write_text('single point\nhk1 1 1 0\n')
    main(['log', '--check'])
    status = {ln.split()[2]: ln.split()[-1] for ln in capsys.readouterr().out.splitlines()}
    assert status == {'build': 'unchanged', 'dump': 'unchanged', 'update': 'changed', 'parrep': 'changed'}


def test_mentions():
    data = {'sources': [{'path': r'C:\x\Book.xlsm', 'sha256': 'abcdef0123'}], 'output': {'path': '/y/case.pst'}}
    assert mentions(data, 'book.xlsm') and mentions(data, 'case.pst') and mentions(data, 'ABCDEF')
    assert not mentions(data, 'other.pst')


# ---------------------------------------------------------------------- bundle
def test_bundle_default_contents(project, capsys):
    main(['bundle', 'model.pst'])
    out = capsys.readouterr().out
    names = zipfile.ZipFile(project / 'model.zip').namelist()
    assert names == ['model.pst', 'model.pst.manifest.json', 'model.tpl', 'model.in', 'heads.ins', 'flow.ins', 'model.py']
    assert 'written model.zip: 7 files' in out
    m = find_manifests([str(project / 'model.zip.manifest.json')])[0]
    assert m['command'] == 'bundle' and m['output']['files'] == 7 and m['output']['missing'] == []
    assert {os.path.basename(s['path']): s['role'] for s in m['sources']}['model.py'] == 'model command'


def test_bundle_sources_outputs_extra_and_list(project, capsys):
    main(['bundle', 'model.pst', 'run.zip', '--sources', '--outputs', '--extra', '*.res'])
    names = set(zipfile.ZipFile(project / 'run.zip').namelist())
    assert {'heads.out', 'flow.out', 'control.csv', 'par.csv', 'model.res'} <= names
    main(['bundle', 'model.pst', '--list'])
    out = capsys.readouterr().out
    assert 'would add' in out and '(nothing written)' in out and not (project / 'model.pst.zip').exists()


def test_bundle_reports_missing_files(project, capsys):
    os.remove(project / 'model.in')
    main(['bundle', 'model.pst', 'run.zip'])
    out = capsys.readouterr().out
    assert 'MISSING    model input        model.in' in out and '1 missing' in out
    assert 'model.in' not in zipfile.ZipFile(project / 'run.zip').namelist()
    with pytest.raises(SystemExit):
        main(['bundle', 'model.pst', 'run2.zip', '--strict'])
