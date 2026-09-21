# makePst: A Reproducible and Auditable Spreadsheet Workflow for PEST Model Calibration

**Gengxin Ou** (corresponding author; mou@sspa.com), **Zhaowei Wang** (JWang@sspa.com)
S.S. Papadopulos & Associates, Inc.; 1801 Rockville Pike, Suite 220, Rockville, MD 20852

**Article Impact Statement.** makePst links spreadsheet project records and PEST control files for reproducible, auditable groundwater model calibration.

---

## The problem: two representations of one calibration

Parameter estimation with the PEST family of software — PEST (Doherty 2015), PEST_HP (Doherty 2020), and PEST++ (White et al. 2020) — is routine in groundwater modeling. Every run is defined by a control file: a text document listing parameters and their bounds, observations and their weights, parameter and observation groups, prior information, the model command, and the template and instruction files that connect PEST to the model. For a highly parameterized model this file runs to tens of thousands of lines.

For such applications, control files are rarely practical to maintain manually, and in many consulting workflows the working calibration record is instead kept in spreadsheets. A workbook holds one sheet per parameter type, an observation sheet per data source, helper columns carrying model layer or pilot-point indices, and formulas that compute observation weights — balancing groups against one another, down-weighting a period of record, scaling a bound from a native value. In many projects the workbook becomes the principal human-readable record used for internal review, client communication, and tracking calibration decisions. The control file is derived from it.

Scripting toolkits do not remove the need for this record. pyEMU (White et al. 2016) can generate a parameterization and write a control file, and in a fully scripted workflow the code is the record. In many project teams, however, calibration decisions are reviewed by people who do not write the supporting scripts. Spreadsheet formulas and annotations make those decisions visible in the same record used for review. makePst therefore retains the workbook as the project interface while linking it reproducibly to the executable control file.

The derivation is where things go wrong. Counts in the control file must match the tables; parameter groups must be defined before they are used; a tied parameter must point at a parameter that exists and is neither tied nor fixed; a regularization equation must not cite a fixed parameter; every parameter must appear in a template file and every observation in an instruction file. Some inconsistencies prevent a PEST run from starting; others leave a syntactically valid control file whose contents no longer reflect the modeler's intended setup. After a run the traffic reverses: best parameter values, residuals, and — for PESTPP-IES — a chosen realization must go back into the workbook, by name, into the right rows of the right sheets, without overwriting the formulas that produced the weights.

A PEST_HP or PESTPP-IES run for a regional transient model occupies a cluster for hours to days. Errors caught at start-up cost little, whereas an internally valid but unintended configuration — a parameter fixed that should have been adjustable, a weight a formula would have set differently, an earlier iteration's values — can consume a complete run before review exposes the problem. Later, when a reviewer asks which workbook produced a given control file, or what changed between two runs that behaved differently, a text comparison of 40,000 lines is not an answer. Three needs follow: to check a configuration before PEST sees it, to compare two configurations by meaning rather than by text, and to record what produced each file.

Development of makePst was motivated by experience with a conversion script used for a regional model through more than a dozen calibration runs: it wrote the control file, but met none of those needs, and results went back into the workbook by hand. What was missing was a layer that treats the spreadsheet as a first-class, bidirectional interface — keeping it and the control file demonstrably consistent, and preserving the user's formulas when results are written back.

## What makePst does

makePst (installed and invoked as `makepst`) is an open-source Python package with a command-line interface; Excel itself is optional. It uses one structured representation for the calibration tables, control variables, model commands, template and instruction pairs, and PEST++ options, so the same consistency rules apply in both directions (Figure 1).

Two design decisions underpin auditability. Every command that produces a file writes a sidecar manifest containing the package, Python, and dependency versions, the command line, input hashes and sheets, and the output hash and dimensions, so a control file can be traced to its source workbook. And round-tripping is defined semantically for supported content: formatting, case, numeric representation, and some ordering may be normalized.

**`build`** reads Excel worksheets or CSV files and writes a PEST-family control file. Tables may span many worksheets, while columns that are not PEST fields — formulas, indices, notes — are ignored. Counts are calculated rather than entered. Tied parameters, regularization equations generated from preferred values, PEST_HP keywords, and PEST++ options are supported. The build command can be stored in the workbook itself.

**`validate`** reports without changing files. It checks duplicate names, groups, ties, bounds, prior equations, and name lengths, then cross-checks parameters and observations against template and instruction files. Optionally, a small interpreter runs the instructions against model output. Validation accepts a workbook before a control file exists and returns a nonzero status on errors, but complements rather than replaces PEST's own checker.

**`dump`** is the reverse of `build`: it reads a control file into a workbook whose sheets `build` can read back. This is how an inherited control file enters the spreadsheet workflow, or how a workbook is recovered when only the control file survives.

**`update`** returns parameter, residual, or PESTPP-IES ensemble results to an existing workbook. It matches rows by name across worksheets and writes only requested columns, leaving formulas alone unless instructed otherwise. Residual updates also report objective-function contributions by observation group. The openpyxl backend needs no Excel; xlwings drives Excel so charts and macros survive and formulas recalculate.

**`parrep`** writes parameter values or an ensemble realization into a new control file.

**`diff`** compares two control files, or a file and workbook, semantically and with numeric tolerances.

**`provenance`** compares the input and output hashes recorded in a manifest with the files on disk, reporting changed or missing files. Unlike `validate`, it checks file identity rather than PEST content. **`log`** lists every manifest under a project folder as a ledger — when, which command, which output from which sources — and can be filtered by file name or hash, so the question "which runs used that version of the workbook?" is answered from the command line.

**`init`** writes a starter workbook that already builds a valid control file.

## Demonstration on a regional model

The demonstration uses the calibration workbook of a regional transient MODFLOW model; the workbook is included with the release, and the accompanying script reproduces the build, round-trip, and openpyxl-update metrics reported below. makePst reads 20 sheets: control variables, parameter groups, eight parameter sheets (horizontal and vertical hydraulic conductivity, specific storage, specific yield, streambed conductance, boundary heads, recharge multipliers, and miscellaneous parameters), seven observation sheets spanning steady-state and transient heads, transient head differences, streamflow, stream leakage, and lake stages, an input/output sheet, and two PEST++ option sheets. Many observation weights are formulas that look up the number of records per well and a group-balancing factor.

*Build.* One command produces a 2.6-MB control file of 43,549 lines — 1,068 parameters in 12 groups, 41,747 observations in 12 groups, 159 regularization equations generated from the parameter sheets, 18 template and 7 instruction files — in about ten seconds on a laptop, most of it spent reading Excel. The manifest records the workbook's hash and the 20 sheet names.

*Round trip.* `dump` writes the control file to a fresh workbook; `build` from that workbook's stored command regenerates the control file; `diff` reports no semantic differences between the original and the rebuilt configuration. For this project the two makePst-generated files were also byte-identical. This tests internal consistency, not whether the original build captured every intended workbook value.

*Validation.* `makepst validate` and PEST's own checker, pestchek 17.5, both report no errors on the built file and agree on their shared warnings: three parameter groups containing only fixed or tied parameters, an observation group that is listed but empty, `MAXSING` above the number of adjustable parameters, and the memory saving available from switching off covariance output. pestchek additionally warns that four control variables are PEST_HP-specific; makePst treats them as supported and reports them as a note. Beyond pestchek, makePst checks that the referenced template, instruction, and model files and the model command exist. In a second project with 164 adjustable parameters, both programs identified the same error: a factor-limited parameter whose bounds differ in sign.

*Results back.* `update` with a parameter file and a residuals file writes values into the eight parameter sheets (1,068 rows matched) and modelled values and residuals into the seven observation sheets (41,747 rows), plus an objective-function sheet, leaving every weight formula untouched. With the xlwings backend, the parameter update of the production workbook itself — 27 worksheets, macros, a chart, and 12,719 formulas on the parameter sheets — took 9.7 s; the saved copy kept every worksheet, formula, and macro, and its 1,068 `PARVAL1` values equal the parameter file's.

**Table 1.** Demonstration workflow and wall-clock times on a Windows 11 laptop with Python 3.12.

| Step | Command | Time | Result |
|---|---|---|---|
| Workbook → control file | `makepst build` | 7–12 s | 1,068 par, 41,747 obs, 159 prior; 43,549 lines |
| Control file → workbook | `makepst dump` | 2–6 s | 9 sheets, incl. the build command |
| Workbook → control file | `makepst build` | 2–5 s | byte-identical to the original |
| Original vs rebuilt | `makepst diff` | ~1 s | no differences |
| Results → workbook copy (openpyxl) | `makepst update` | 12–26 s | 1,068 + 41,747 rows; formulas untouched |
| Parameters → production workbook (xlwings, Excel) | `makepst update --backend xlwings` | 9.7 s | 1,068 rows in 8 of 27 sheets; macros, chart, formulas kept |

## Validation, scope, and limitations

The test suite at the submitted version contains 154 tests, two of which need the demonstration workbook and are skipped without it; continuous integration runs the suite on Linux and Windows with Python 3.9, 3.11, and 3.13. Tests include golden-file builds from a synthetic workbook, read–write identity, `dump`-then-`build` equality, multi-sheet workbook updates with formula protection, provenance checks, ensemble selection, validation rules, the instruction interpreter, and the documented tutorial.

makePst reads and writes classic PEST control files, the PEST_HP extensions used in the demonstration, and PEST++ control files in both the classic and the version-2 external-table formats; it reads `.par`, `.res`/`.rei`, and PESTPP-IES ensemble and objective-function files. It does not perform calibration, uncertainty analysis, geostatistical parameterization, or run management. The instruction interpreter behind `validate` follows the manual but is not PEST, and its findings are reported as warnings; the documentation recommends running pestchek on every generated file. Recognized pass-through sections are retained verbatim; unrecognized sections are dropped with a warning. `dump` recovers supported control-file content in nine standardized sheets, not the original workbook's organization, formulas, or notes. Excel-faithful updates require Excel and xlwings; the openpyxl backend keeps macros but not charts and does not recalculate formulas, so a workbook it has updated must be opened, recalculated, and saved in Excel before it is built from again — otherwise cached formula values are missing or stale, and `build` warns when they are.

pyEMU provides a broader Python framework for PEST++ interface construction, parameterization, ensembles, geostatistics, and uncertainty analysis (White et al. 2016). makePst instead focuses on maintaining a bidirectional, auditable relationship between spreadsheet project records and executable PEST configurations. The packages are complementary: makePst-generated control files can enter pyEMU workflows, and PEST and PEST++ results can be returned to spreadsheets through makePst.

## Significance for practice

The immediate benefit is reproducibility: a calibration defined by a workbook and a one-line command can be rebuilt by another person on another machine and shown by `diff` to be the same, and the manifests, listed with `log` and checked with `provenance`, make that claim verifiable years later, when a model is reviewed by a client or an agency. The second benefit is that the reviewed record and the executable file stop drifting apart. Modelers keep weighting in formulas, annotating in notes, and splitting parameters across sheets by type, and still obtain a control file whose name-level errors are caught before a run rather than after; results come back into the same workbook without a copy-and-paste step. Because CSV is accepted wherever a sheet is, the same workflow runs without Excel in a continuous-integration job or on a cluster.

By treating spreadsheets and control files as reproducibly linked representations of the same calibration configuration, makePst lets groundwater modelers retain familiar review practices while making control-file construction, checking, and result transfer reproducible. It is intended as a small, auditable layer within existing PEST and PEST++ workflows, not a replacement for any part of them.

## Software availability

makePst is available under the MIT License at https://github.com/ougx/makePst. The version described here is 0.3.0 (tagged `v0.3.0`; also on PyPI as `makepst`). The repository contains a four-parameter tutorial and the script used for the build, round-trip, and openpyxl-update metrics (`paper/reproduce.py`). The regional-model workbook used for the demonstration is included in the GitHub release assets.

## Conflict of Interest

The authors are developers of makePst. The software is open source under the MIT License.

## References

Doherty, J. 2015. *Calibration and Uncertainty Analysis for Complex Environmental Models.* Brisbane, Australia: Watermark Numerical Computing.

Doherty, J. 2020. *PEST_HP: PEST for Highly Parallelized Computing Environments.* Brisbane, Australia: Watermark Numerical Computing.

White, J.T., M.N. Fienen, and J.E. Doherty. 2016. A python framework for environmental model uncertainty analysis. *Environmental Modelling & Software* 85: 217–228. https://doi.org/10.1016/j.envsoft.2016.08.017

White, J.T., R.J. Hunt, M.N. Fienen, and J.E. Doherty. 2020. *Approaches to Highly Parameterized Inversion: PEST++ Version 5, a Software Suite for Parameter Estimation, Uncertainty Analysis, Management Optimization and Sensitivity Analysis.* U.S. Geological Survey Techniques and Methods 7-C26. https://doi.org/10.3133/tm7C26

---

**Figure 1.** makePst workflow linking spreadsheet-based project records and PEST-family control files. Calibration definitions are built into and reconstructed from control files through a common structured representation; validation and semantic comparison support QA/QC, while parameter, residual, and ensemble results are returned to existing workbooks by name. The inset is an abbreviated manifest from the demonstration build; complete manifests record software, commands, timestamps, source sheets and hashes, output hashes, and project dimensions. [Figure file: `paper/figure1.svg`, generated by `paper/make_figure1.py`.]
