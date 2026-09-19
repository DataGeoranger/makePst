# Changelog

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
