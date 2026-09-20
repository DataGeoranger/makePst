# Changelog

## 0.2.0 (2026-09-19)

- `update`: the xlwings backend reads only headers, name and target columns, writes contiguous
  cells in one call per run, suspends events and calculation while writing and recalculates
  once before saving (1,068 parameters over eight sheets of a 27-sheet workbook: ~9 s, was
  minutes); `--par` with `--pst` no longer rewrites the observation sheets
- `tempchek`: check a template file or write model input files from parameter values, with
  PEST's number writer (maximum precision in the space, `PRECIS` / `DPOINT`, one word per
  parameter, right-justified; checked against `tempchek.exe`); for a template + `.par` file
  or for a whole case
- `inschek`: check an instruction file or read a model output file with it into an `.obf`
  file, for one file or a whole case
- `validate`: values that cannot be written into their template space are errors; a line
  advance not at the start of an instruction line and `t` / fixed instructions moving left
  are errors (INSCHEK's rules); three more pestchek warnings (empty observation group,
  `ICOV`/`ICOR`/`IEIG` with more than 300 adjustable parameters, PEST_HP-only variables —
  the last as a note); an all-zero-weight observation group is now a note, not a warning
- `update`: cells inside array formulas or dynamic-array spill ranges are left alone (Excel
  refuses them; xlwings no longer shows a dialog); names present on only one side are reported
  with counts and examples
- `validate`: pestchek's rules added (parameter data, groups, observations, prior information,
  ~60 control-variable ranges and consistency rules, template and instruction syntax), derived
  from PEST 17's `pestchek.F` / `cheksub.F`; file paths resolved from the directory PEST runs
  in, not only the control file's folder

## 0.1.0 (2026-09-19)

First packaged release; replaces the single-file `makePst.py` script.

- `init`: starter workbook with headers, defaults, descriptions, drop-down lists, comments and
  a `BUILD` sheet
- `build`: Excel/CSV tables -> control file; sheet globs (`book,PAR_*`); a workbook with a
  `BUILD` sheet as the only argument; counts computed; PEST_HP keyed tokens and
  `++` options; regularisation equations from `PRIOR`/`WEIGHT` columns; validation of tied
  targets, groups, prior references and bounds
- `dump`: control file -> workbook with a `BUILD` sheet that rebuilds it
- `update`: `.par` / `.res` / `.rei` / PESTPP-IES ensembles into an existing workbook, matched
  by name across sheets; formula cells protected; `--sheet` / `--group` filters; `--real`;
  `PHI` sheet (objective function by observation group) and `PHI_IES` (realization phis)
  whenever residuals are available
- `validate`: pestchek-style report on a control file or workbook: table checks, missing
  files, parameter / observation names against template and instruction files, optional run
  of instruction files against model outputs; exit 1 on errors
- PEST++ version-2 control files (`pcf version=2`, keyword control data, external csv
  tables) are read and written (`--v2`); observation covariance files are kept
- `diff`: semantic comparison of two control files / workbooks (tables, effective control
  values, options, io, comments), text report or workbook; exit 1 on differences
- pyEMU bridge: `to_pyemu()` / `from_pyemu()` via a temporary control file (`pyemu` extra)
- provenance: every producing command writes `<output>.manifest.json` (version, command
  line, source hashes and sheets, output hash and counts)
- `parrep`: `.par` or IES realization into a control file (or a workbook with a `BUILD` sheet),
  with `--set NAME=VALUE`
- Fixes over the old script: `jacupdate` was never written; values were truncated to 6
  significant digits; `phistopthresh` could not be set; SVD / regularisation values in the
  CONTROL sheet were ignored; prior information in estimation mode produced an invalid file
