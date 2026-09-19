# makePst

[![tests](https://github.com/ougx/makePst/actions/workflows/tests.yml/badge.svg)](https://github.com/ougx/makePst/actions/workflows/tests.yml)

*makePst: A Reproducible and Auditable Spreadsheet Workflow for PEST Model Calibration*

`makepst` builds PEST / PEST_HP / PEST++ control files (`.pst`) from Excel or CSV tables,
reads control files back into editable workbooks, and returns calibration results
(`.par`, `.res`/`.rei`, PESTPP-IES ensembles) into the workbook you already maintain.

```
(nothing)                              ->  starter workbook  makepst init
.pst or workbook + tpl/ins files        ->  pestchek-style report  makepst validate
Excel / CSV tables                     ->  .pst              makepst build
.pst                                   ->  editable workbook makepst dump
.par / .res / .rei / IES ensemble      ->  existing workbook makepst update
.par or IES realization (+ tweaks)     ->  new .pst          makepst parrep
two .pst / workbooks                   ->  what changed      makepst diff
```

See [What round-tripping preserves](#what-round-tripping-preserves) for the exact guarantees
and the [compatibility table](#compatibility) for which PEST dialects and sections are covered.

## Why makepst?

A PEST setup of a few thousand parameters and tens of thousands of observations is easier to
review in a spreadsheet than in a 40,000-line text file. In practice most calibration teams
already keep one: the workbook holds the parameter tables per group, weights computed by
formulas, helper columns (layer, pilot-point index, native values), and a run history. The
control file is derived from it.

`makepst` makes that derivation deterministic and safe:

- **The workbook is the source of truth.** The control file is rebuilt from it with one
  command; the build command itself can live in the workbook (`BUILD` sheet).
- **Counts are computed, never typed.** `npar`, `nobs`, `npargp`, `nprior`, `nobsgp`,
  `ntplfle`, `ninsfle` always match the tables.
- **Validation before PEST sees the file.** Duplicate names, undefined parameter groups,
  tie targets that don't exist, regularisation equations that reference fixed or tied
  parameters, initial values outside bounds — reported by name, not as a PEST run-time error.
- **Results flow back.** Best parameters, residuals or an IES realization are written into
  the existing workbook by name, across however many sheets the tables are split over,
  without touching formulas, macros or helper columns.
- **PEST_HP tokens** (`win_mrun_hours=`, `uptestmin=`, `absparmax(1)=…`) and `++` PEST++
  options are first-class, so no post-editing of the generated file.
- **Fits existing workflows.** The `build` command line is the same one the original
  single-file script accepted; batch files keep working.

## Install

Not on PyPI yet. Until the first release:

```
pip install git+https://github.com/ougx/makePst
pip install "makepst[excel] @ git+https://github.com/ougx/makePst"   # + xlwings (see update)
pip install "makepst[pyemu] @ git+https://github.com/ougx/makePst"   # + pyEMU (see the bridge)
```

Requires Python ≥ 3.9, pandas ≥ 2.0, numpy, openpyxl ≥ 3.1. Installing adds the `makepst`
command; `python -m makepst` is equivalent, and `python makePst.py` works from a checkout
without installing.

## Starting from nothing

```
makepst init project.xlsx
```

writes a workbook that already builds a valid control file: every sheet with the headers
`build` expects and a few example rows, a `CONTROL` sheet listing every PEST variable with its
default and a one-line description, drop-down lists where PEST allows only fixed words
(`PARTRANS`, `INCTYP`, `FORCEN`, `DERMTHD`, `IO!TYPE`, the on/off control variables), header
comments explaining each column, frozen header rows, and a `BUILD` sheet with the build
command. Replace the example rows with your own and run that command.

## Two-minute tutorial

`examples/minimal/` holds a four-parameter, four-observation setup as CSV tables, its
template / instruction files, a toy `model.py`, and a fake `model.par` and `model.res` (this
is also run by the test suite):

```bash
cd examples/minimal            # on Windows cmd, replace the trailing \ with ^

# 1. tables -> control file (also writes dump.tpl, a template that echoes every parameter)
makepst build model.pst regul --set_ctl_csv control.csv --add_pargp_csv pargp.csv \
    --add_par_csv par.csv --add_obs_csv obs.csv --add_io_csv io.csv --add_comment "minimal example"

# 2. check it against the template / instruction / output files, like pestchek
makepst validate model.pst --outputs

# 3. control file -> workbook (CONTROL / PARGP / PAR / OBS / PRIOR / IO sheets + a BUILD sheet)
makepst dump model.pst model.xlsx

# 4. results -> a copy of the workbook: PARVAL1 from .par, MODELLED / RESIDUAL from .res
makepst update model.xlsx --par model.par --res model.res --out model-results.xlsx

# 5. best parameters -> a new control file for a final run
makepst parrep model.pst model.par model-final.pst --set noptmax=0
```

Open `model.pst` to see what the tables became: `hk3` is tied to `hk1` (the `TIETO` column),
`hk1` and `hk2` got regularisation equations from their `PRIOR`/`WEIGHT` columns
(`log(hk1) = log10(25)`, `log(hk2) − log(hk1) = 0`), `lamforgive` and `maxsing 3` came from
`control.csv`, and every count on the control-data lines was computed.

## Commands

### init — starter workbook

```
makepst init project.xlsx [--name case] [--force]
```

See [Starting from nothing](#starting-from-nothing). `--name` sets the control-file name in
the `BUILD` command (default: the workbook's name). Existing files are not overwritten
without `--force`.

### validate — pestchek-style checks

```
makepst validate model.pst --outputs
makepst validate book.xlsm --strict
```

See [Validation](#validation). Template and instruction paths are resolved relative to the
control file (or workbook); `--base_dir` overrides that. `--strict` also fails on warnings,
`--quiet` hides the informational lines.

### build — tables → .pst

```
makepst build out.pst [estimation|regularisation|prediction|pareto]
    --set_ctl_xls book.xlsm,CONTROL          (or --set_ctl_csv file.csv)
    --add_pargp_xls book.xlsm,PARGP
    --add_par_xls   book.xlsm,PAR_*          (repeatable; sheet names may be globs)
    --add_obs_xls   book.xlsm,OBS_*
    --add_io_xls    book.xlsm,IO  --add_pp_xls book.xlsm,PPcntl
    [--add_tied_xls ...] [--add_prior_xls ...] [--add_comment "text"] [--add_comment_xls ...]
    [--fill_parval run.par [--real NAME]] [--ss] [--no_dump_tpl] [--v2]
```

Each `--add_*` takes `book,SHEET` (`_xls`) or a csv path (`_csv`) and may be repeated;
tables split across sheets are concatenated. The sheet name may be a glob:
`--add_par_xls tr13.xlsm,PAR_*` adds every `PAR_…` sheet in workbook order. Headers are
case-insensitive. `makepst build book.xlsm [--out x.pst]` runs the command stored in the
workbook's `BUILD` sheet instead. The mode argument
overrides `pestmode` in the CONTROL sheet; adding prior information switches to regularisation.
`--ss` drops `ss*`/`sy*` parameters and groups (steady-state runs of a transient setup).

| table   | columns |
|---------|---------|
| CONTROL | `NAME`, `VALUE` in the first four columns (`LINE`, `NAME`, `DEFAULT`, `VALUE`); blank values use the built-in default. Any variable of the control data, SVD, LSQR, AUI, SVD-assist or regularisation sections: `noptmax`, `jacupdate`, `lamforgive`, `win_mrun_hours`, `absparmax(1)=0.1 absparmax(2)=20`, `svdmode`, `phimlim`, … Counts are ignored (computed). |
| PARGP   | `PARGPNME INCTYP DERINC DERINCLB FORCEN DERINCMUL DERMTHD` (+ optional `SPLITTHRESH SPLITRELDIFF SPLITACTION`) |
| PAR     | `PARNME PARTRANS PARCHGLIM PARVAL1 PARLBND PARUBND PARGP SCALE OFFSET DERCOM`; optional `TIETO`, and `PRIOR` / `WEIGHT` (regularisation, below). Other columns are ignored, so helper columns are fine. |
| TIED    | two columns: parameter, parameter it is tied to (alternative to a `TIETO` column) |
| OBS     | `OBSNME OBSVAL WEIGHT OBGNME` |
| OBSGP   | `OBGNME`, optional `COVFILE` — observation-group order and covariance matrix files (rarely needed) |
| PRIOR   | `PINME EQ WEIGHT OBGNME` — explicit prior-information equations |
| IO      | `TYPE` (`cmd` / `tpl` / `ins`), `IN`, `OUT` |
| PP      | first two columns: PEST++ option name, value → `++name(value)` |

**Regularisation from the parameter table.** In regularisation mode each adjustable
parameter with a `PRIOR` and a positive `WEIGHT` gets an equation: a numeric `PRIOR` gives
`1.0 * log(p) = log10(v)` (or `1.0 * p = v` for untransformed parameters); a `PRIOR` naming
another parameter gives `1.0 * log(p) − 1.0 * log(q) = 0`. The group is `regul` + parameter
group, truncated to 12 characters.

### dump — .pst → workbook

```
makepst dump run.pst run.xlsx [--split]
```

Writes `CONTROL`, `PARGP`, `PAR` (with `TIETO`), `OBS`, `PRIOR`, `IO`, `PP`, `NOTES` (the
header comments) and `BUILD` — the command that rebuilds the control file from this
workbook. `--split` writes one `PAR_<group>` and `OBS_<group>` sheet per group instead of
`PAR` and `OBS`. Use it to bring an inherited control file into the spreadsheet workflow, or
to recover a workbook that was lost.

### update — results → existing workbook

```
makepst update book.xlsm --par run.par                          # PARVAL1
makepst update book.xlsm --res run.res                          # adds MODELLED / RESIDUAL
makepst update book.xlsm --pst run.pst --par_cols PARVAL1,PARTRANS,PARLBND,PARUBND
makepst update book.xlsm --par run.3.par.csv --real best        # PESTPP-IES ensemble
makepst update book.xlsm --obs_csv run.3.obs.csv --pst run.pst  # IES simulated values
    [--sheet "PAR_*"] [--group hk,sy] [--overwrite_formulas] [--out copy.xlsm] [--backend openpyxl|xlwings]
```

> **`update` saves in place unless `--out` is given.** Use `--out` the first time, and keep
> the workbook closed in Excel while it runs.

Every worksheet whose header row contains `PARNME` (or `OBSNME`) is matched row by row on the
name, so tables spread over several sheets are all found; only the requested columns are
written and only for names present in the source. Cells that hold formulas are left alone
unless `--overwrite_formulas`. `--sheet` (glob, case-insensitive) restricts the worksheets;
`--group` restricts the parameter / observation groups (a `.par` file carries no groups, so
add `--pst` to supply them).

PESTPP-IES ensembles (`case.N.par.csv`, `case.N.obs.csv`) are recognised by their
`real_name` header. `--real` picks the realization: a name (`base`, `17`) or `best` — the
lowest phi for that iteration in `case.phi.actual.csv` next to the file. Default `base`. An
observation ensemble writes `MODELLED`; with `--pst` also `RESIDUAL` (measured − modelled).

With residuals (`--res`, or `--obs_csv` plus `--pst`) `update` also writes a **`PHI`** sheet —
the objective function by observation group as PEST reports it at the end of a run: number of
observations and of weighted ones, phi (Σ(w·r)²) and its fraction of the total, RMS / mean /
max-abs residual of the weighted observations in their own units, and the worst observation,
with a `TOTAL` row. For an IES ensemble with `case.phi.actual.csv` beside it, a **`PHI_IES`**
sheet lists every realization's phi for that iteration, sorted, with mean / std / min / max.
Both sheets are rewritten on each run (`--no_phi` to skip).

Two backends: **xlwings** (used when installed; drives Excel invisibly, so everything in the
workbook is preserved and formulas recalculate; Windows/macOS with Excel) or **openpyxl**
(no Excel needed; keeps VBA macros; drops charts and images; formula results are stale until
Excel next opens the file). The backend used is printed.

### parrep — .par values → new .pst

```
makepst parrep run.pst run.par next.pst [--set noptmax=0] [--set NAME=VALUE ...] [--v1|--v2]
makepst parrep run.pst run.3.par.csv next.pst --real best
makepst parrep book.xlsm run.par next.pst                       # base is the workbook
```

Like PEST's PARREP: `PARVAL1` is replaced from a `.par` file or an IES realization and a new
control file is written; `--set` changes control values on the way. All supported content of
the input control file is preserved semantically (see below); adjustable parameters that end
up outside their bounds are reported.

With a **workbook** as the base, the control file is first built from the command in the
workbook's `BUILD` sheet (`dump` writes one; for a hand-made workbook paste the build command
into column A, one option per row). File names in it that match the workbook's own name refer
to that workbook; other relative names resolve against the workbook's folder. Note that this
route rebuilds from the workbook's *current* state, so any edits made since the original
control file was written are picked up too.

### diff — what changed

```
makepst diff tr12.pst tr13.pst [--xlsx changes.xlsx] [--rtol 1e-9] [--max_rows 50]
makepst diff tr13.xlsm tr13.pst                # is the control file still what the workbook says?
```

Compares the tables, not the text: parameters and observations added, removed or changed
(column by column), prior-information equations, parameter groups, effective control values
(defaults filled in, so a file and a workbook compare fairly), `++` options, template /
instruction pairs, command lines and header comments. Numbers are compared with a relative
tolerance, so `49.7377` vs `49.73775` shows up at the default `1e-9` and disappears at
`--rtol 1e-5`. Prints a table per section and a one-line summary; `--xlsx` writes the same
tables to a workbook for review. Exits 1 when there are differences, like `diff`.

## What round-tripping preserves

`dump` → `build` and `read_pst` → `write_pst` are **semantically lossless for supported
content**, not byte-identical: `read → write → read` is an identity, and `dump` → `build`
reproduces the same text as `read → write`. Concretely:

Preserved: every parameter, group, observation, prior-information equation, tied pair,
template/instruction pair, command line, `++` option, header comment, control-data value
(including PEST_HP keyed tokens), SVD / LSQR / AUI / SVD-assist / regularisation values, and
the verbatim text of `* sensitivity reuse`, `* derivatives command line`, `* predictive
analysis` and `* pareto`.

Normalised: parameter, observation and group names are lower-cased (PEST is
case-insensitive); numbers are written with 11 significant digits; whitespace and column
alignment are makepst's own; comments *inside* sections are dropped; observation groups are
listed in first-use order (or the order of the source file when reading a `.pst`).

Also preserved: covariance-file references in `* observation groups` (an `OBSGP` sheet on
`dump`), and the control-file **format version**: a PEST++ version-2 file (`pcf version=2`,
`* control data keyword`, `* … external` csv tables) reads into the same tables and is
written back as version 2 unless `--v1` is given; `--v2` writes any control file in that
format, with `case.par_data.csv` / `obs_data` / `pargp_data` / `prior_data` beside it. Both
versions of the same content are identical after reading (`makepst diff` says so).

Not preserved: any unrecognised section (dropped with a warning naming it).

## Compatibility

| | |
|---|---|
| PEST dialects | PEST, PEST_HP (`win_mrun_hours=`, `uptestmin=`, `uptestlim=`, `absparmax(n)=`), PEST++ (`++name(value)` options) |
| Control-file sections | control data, singular value decomposition, lsqr, automatic user intervention, svd assist, parameter groups, parameter data (incl. tied pairs), observation groups, observation data, model command line, model input/output, prior information (with `&` continuation lines), regularisation. Kept verbatim: sensitivity reuse, derivatives command line, predictive analysis, pareto. |
| File formats | classic (version 1) and PEST++ version 2 (`pcf version=2`, `* control data keyword` with control variables and `++` options, `* … external` csv tables with `sep=` / `missing_values=`, `partied` column); observation covariance files in `* observation groups` |
| Not supported | unknown sections — dropped with a warning |
| Result files | `.par`, `.res` / `.rei`, PESTPP-IES `case.N.par.csv` / `case.N.obs.csv` / `case.phi.actual.csv` |
| Table inputs | `.xlsx` / `.xlsm` sheets (openpyxl), `.csv` |
| Workbook update | openpyxl backend on any platform (macros kept, charts/images dropped, no recalculation); xlwings backend on Windows/macOS with Excel (everything kept, recalculated) |
| Platforms | CI runs the suite on Linux and Windows for Python 3.9, 3.11 and 3.13. macOS is expected to work but is not exercised in CI. |
| Python | ≥ 3.9; pandas ≥ 2.0 (tested with 2.3 and 3.0), numpy, openpyxl ≥ 3.1; optional xlwings, pyemu, pytest |

## Validation

Two layers. `Pst.validate()` runs before every write (`build`, `dump`, `parrep`, `write_pst`)
and enforces **internal consistency** of the tables, changing what it can and refusing what it
cannot:

| check | outcome |
|---|---|
| no parameters / no observations | error |
| duplicate parameter, observation or prior-information names | error |
| parameter group used but not defined | error |
| tied parameter whose target is missing, or tied to a tied parameter | error |
| tied to a fixed parameter | parameter becomes fixed (message) |
| parameter group defined but unused | dropped from the file |
| prior equation referencing a fixed, tied or missing parameter | dropped (message) |
| adjustable `PARVAL1` outside `[PARLBND, PARUBND]` | warning |
| control value that is computed (`npar` …) or unknown | ignored (warning) |

`makepst validate` is the **pestchek-style report**: it changes nothing, looks beyond the
tables at the files the control file points to, and exits 1 on errors so a batch file can
stop:

```
makepst validate model.pst [--outputs] [--strict] [--quiet] [--base_dir DIR]
makepst validate tr13.xlsm            # a workbook with a BUILD sheet is built first, in memory
```

| check | severity |
|---|---|
| everything in the table above, reported rather than fixed | error / warning |
| `PARTRANS` not log/none/fixed/tied; non-numeric values; `PARLBND` > `PARUBND`; log parameter with a non-positive lower bound | error |
| negative observation weight; all weights zero | error / warning |
| malformed prior equation; non-numeric right-hand side; `log()` used on a non-log parameter or vice versa | error |
| `DERCOM` beyond the number of model command lines | error |
| name longer than PEST's limit (12 parameter / 20 observation / 12 group; PEST++ allows 200) | warning |
| section in the `.pst` that makepst drops on read | warning |
| template or instruction file missing; bad `ptf` / `pif` line | error |
| parameter cited in no template; template citing an unknown parameter | error |
| observation read by no instruction file, by two files, or twice in one; unknown observation in an instruction file | error |
| model command / model-input folder not found next to the control file | warning |
| `--outputs`: each instruction file run against its model output file when present | note (success) / warning (failure) |

The `--outputs` interpreter follows the PEST manual (primary and secondary markers, `l`, `w`,
`t`, `!name!`, `[name]c1:c2`, `(name)c1:c2`, `dum`, `&` continuation) and catches the classic
mistakes — a `w` too few so a label is read instead of a number, a marker that never appears
— but it is not PEST. Keep running PEST's own checker before a long run:

```
pestchek model            # PEST / PEST_HP
pestpp-glm model.pst      # PEST++ reports problems on start-up
```

## Audit trail: the manifest

`build`, `parrep`, `dump` and `update` each write a sidecar `<output>.manifest.json` next to
what they produce (`--no_manifest` to skip). It answers "where did this control file come
from?" after the fact:

```json
{
  "makepst": "0.1.0",
  "command": "build",
  "argv": ["build", "tr13.pst", "regul", "--set_ctl_xls", "tr13.xlsm,CONTROL", "..."],
  "created": "2026-09-19T13:51:39-04:00",
  "user": "hydro", "host": "OU13700", "cwd": "D:\\...\\0023-makePst",
  "python": "3.12.12", "pandas": "3.0.5", "platform": "Windows-11-10.0.26200-SP0",
  "sources": [
    {"path": "D:\\...\\tr13.xlsm", "sha256": "9d641a2f...", "size": 3089317,
     "modified": "2026-07-12T03:32:10-04:00", "role": "control",
     "sheets": ["CONTROL", "PARGP", "PAR_HK", "PAR_VK", "...", "PPglm"]}
  ],
  "output": {"path": "D:\\...\\tr13.pst", "sha256": "d93f317d...", "size": 2163331,
             "npar": 1068, "nobs": 41747, "npargp": 12, "nprior": 185, "nobsgp": 12,
             "ntplfle": 18, "ninsfle": 7, "pestmode": "regularisation"}
}
```

Every input file appears once with its SHA-256, size, modification time, role and the sheets
read from it; the output carries its own hash and the section counts. `parrep` adds the
realization and `--set` values (and, from a workbook, the resolved build arguments);
`update` records which sheets were written, how many rows each, how many formula cells were
left alone, and the backend. A hash mismatch between a manifest and the workbook on disk is
the signal that the control file no longer corresponds to the spreadsheet.

## Relationship to pyEMU

[pyEMU](https://github.com/pypest/pyemu) is the broader toolkit: it constructs PEST++
interfaces programmatically (`PstFrom`), runs linear and ensemble-based uncertainty
analysis, and provides geostatistics. `makepst` does one thing pyEMU does not: it treats a
spreadsheet the modeller already maintains as the source of a control file and keeps the two
in sync in both directions, including PEST_HP keywords that pyEMU's control-data model does
not carry. They are complementary — a control file written by `makepst` loads in pyEMU, and
pyEMU's outputs (`.par`, `.res`, ensembles) load into `makepst update`.

There is a direct bridge (the `pyemu` extra):

```python
from makepst import read_pst, to_pyemu, from_pyemu

ppst = to_pyemu(read_pst('tr13.pst'))      # a pyemu.Pst: use pyEMU's Schur, ensembles, plotting, ...
pst = from_pyemu(ppst)                     # back to a makepst Pst, e.g. to dump into a workbook
```

Both directions go through a temporary classic control file, so they depend only on the file
format the two agree on. The tables, `++` options and standard control values survive the
round trip; what does not is exactly what pyEMU's control-data model lacks — PEST_HP keyed
tokens (`absparmax(n)=`, `uptestmin=`, `win_mrun_hours=`), header comments, and the
regularisation section, which pyEMU rewrites with its own defaults. `makepst diff` shows the
difference, and the test suite pins it.

## Python API

```python
from makepst import Pst, read_pst, write_pst, to_workbook, update_workbook, load_table, read_par

pst = read_pst('run.pst')                    # Pst: .par/.obs/.pargp/.prior DataFrames, .control dict, ...
pst.fill_parval('run.3.par.csv', real='best')
pst.set_control({'noptmax': 0})
write_pst(pst, 'run_final.pst', dump_tpl=False)

to_workbook(pst, 'run.xlsx', split=True)
update_workbook('book.xlsm', par='run.par', res='run.res', out='book_results.xlsm',
                sheets=['PAR_*'], groups=['hk'])
```

## Testing

```
python -m pytest tests -q
```

95 tests, no external data needed: a synthetic workbook in the real project layout
(`tests/data/demo.xlsx`, generated by `tests/make_fixture.py`) with a golden control file,
`.par`, `.res` and IES ensemble files. They cover golden-file builds from Excel and CSV, the
`read → write → read` identity, `dump → build` byte equality, workbook updates (multi-sheet
matching, formula protection, sheet/group filters, ensembles), `parrep` from `.par`, ensembles
and workbooks, the `init` starter workbook, `validate` (table checks, template / instruction
cross-checks, the instruction interpreter), the control-section parser, validation errors,
and the README tutorial above.
Two extra tests run against a real 1,000-parameter / 40,000-observation project when its
files are present locally, and two pyEMU bridge tests run when pyemu is installed. CI runs
everything on Linux and Windows.

## Project layout

```
makePst.py          entry point for a checkout (same arguments as `makepst`)
makepst/
  sections.py       control-style sections: field order, defaults, PEST_HP keyed tokens; one table drives render and parse
  pst.py            Pst data model and validate(); .par / .res / ensemble readers
  writer.py         Pst -> .pst text (+ dump.tpl)
  reader.py         .pst text -> Pst
  excel.py          sheets -> Pst; Pst -> workbook; results -> existing workbook
  cli.py            init / validate / build / dump / update / parrep / diff
  diff.py           semantic comparison of two Pst objects
  phi.py            objective function by group from residuals; IES realization phis
  pyemu_bridge.py   to_pyemu / from_pyemu
  checks.py         the validate report: table checks, template / instruction cross-checks, instruction interpreter
  provenance.py     the <output>.manifest.json sidecar
  starter.py        the `init` workbook: control-variable descriptions, example rows, drop-downs
examples/minimal/   the tutorial inputs
tests/              suite + fixture generator
```

## Contributing, issues, citation

Bug reports and feature requests: [GitHub issues](https://github.com/ougx/makePst/issues).
A control file that `makepst` misreads, plus the command used, is the most useful report.
Pull requests should keep `python -m pytest tests -q` green and regenerate the fixture with
`python tests/make_fixture.py` when the writer's output changes.

Changes are listed in [CHANGELOG.md](CHANGELOG.md). To cite, use [CITATION.cff](CITATION.cff)
(GitHub's "Cite this repository" button); a DOI will be added with the first release.

License: MIT.
