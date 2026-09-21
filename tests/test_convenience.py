import json
import os
import warnings

import openpyxl
import pytest

from makepst.cli import main
from makepst.excel import load_table
from makepst.provenance import check_manifest, sha256


def test_provenance_reports_changes_and_missing(tmp_path, capsys):
    source = tmp_path / 'input.txt'
    output = tmp_path / 'output.txt'
    source.write_text('before')
    output.write_text('result')
    sidecar = tmp_path / 'output.txt.manifest.json'
    sidecar.write_text(json.dumps({'sources': [{'path': str(source), 'sha256': sha256(source)}],
                                   'output': {'path': str(output), 'sha256': sha256(output)}}))
    main(['provenance', str(output)])
    assert capsys.readouterr().out.count('unchanged') == 2
    source.write_text('after')
    output.unlink()
    with pytest.raises(SystemExit) as exc:
        main(['provenance', str(sidecar)])
    assert exc.value.code == 1
    report = capsys.readouterr().out
    assert 'changed' in report and 'missing' in report


def test_update_dry_run_does_not_write(tmp_path, capsys):
    book = tmp_path / 'book.xlsx'
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'PAR'
    ws.append(['PARNME', 'PARVAL1'])
    ws.append(['hk', 1.0])
    wb.save(book)
    par = tmp_path / 'values.par'
    par.write_text('single point\nhk 2.0 1.0 0.0\n')
    before = sha256(book)
    main(['update', str(book), '--par', str(par), '--dry_run', '--backend', 'openpyxl'])
    assert sha256(book) == before
    assert not os.path.exists(str(book) + '.manifest.json')
    assert 'hk' in capsys.readouterr().out


def test_build_table_warns_on_missing_formula_cache(tmp_path):
    book = tmp_path / 'formula.xlsx'
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'PAR'
    ws.append(['PARNME', 'PARVAL1'])
    ws.append(['hk', '=1+1'])
    wb.save(book)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        load_table(f'{book},PAR')
    assert any('no cached value' in str(w.message) for w in caught)
