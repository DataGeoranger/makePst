# makePst: A Reproducible and Auditable Spreadsheet Workflow for PEST Model Calibration

**Michael Ou**
[Affiliation], [City, State]; [email]; ORCID [0000-0000-0000-0000]

**Article Impact Statement.** makePst links spreadsheet project records and PEST control files for reproducible, auditable groundwater model calibration.

*Technology Spotlight — Groundwater.* Draft [version/date]. Target ≤ 2,300 words including headings, table, and caption; one figure; ≤ 5 references; no abstract.

---

## The problem: two representations of one calibration

Parameter estimation with the PEST family of software — PEST (Doherty 2015), PEST_HP, and PEST++ (White et al. 2020) — is routine in groundwater modeling. Every run is defined by a control file: a text document listing parameters and their bounds, observations and their weights, parameter and observation groups, prior information, the model command, and the template and instruction files that connect PEST to the model. For a highly parameterized model this file runs to tens of thousands of lines.

For such applications, control files are rarely practical to maintain manually, and in many consulting workflows the working calibration record is instead kept in spreadsheets. A workbook holds one sheet per parameter type, an observation sheet per data source, helper columns carrying model layer or pilot-point indices, and formulas that compute observation weights — balancing groups against one another, down-weighting a period of record, scaling a bound from a native value. In many projects the workbook becomes the principal human-readable record used for internal review, client communication, and tracking calibration decisions. The control file is derived from it.

The derivation is where things go wrong. Counts in the control file must match the tables; parameter groups must be defined before they are used; a tied parameter must point at a parameter that exists and is neither tied nor fixed; a regularization equation must not cite a fixed parameter; every parameter must appear in a template file and every observation in an instruction file. Some inconsistencies prevent a PEST run from starting; others leave a syntactically valid control file whose contents no longer reflect the modeler's intended setup. After a run the traffic reverses: best parameter values, residuals, and — for PESTPP-IES — a chosen realization must go back into the workbook, by name, into the right rows of the right sheets, without overwriting the formulas that produced the weights.

The author's own experience motivated the tool described here. A conversion script that had produced control files for a regional model through more than a dozen calibration runs turned out, on review, to have silently dropped one control variable (the Jacobian-update setting the modeler had entered in the workbook) and to have rounded every parameter and observation value to six significant figures. Neither error stopped PEST; both were invisible in a 40,000-line text file. What was missing was not a converter — pyEMU (White et al. 2016) can write a control file from a DataFrame — but a layer that treats the spreadsheet and the control file as two representations of the same calibration configuration and keeps them demonstrably consistent in both directions.

## What makePst does

makePst (installed and invoked as `makepst`) is an open-source Python package with a command-line interface; it requires only pandas and openpyxl, and Excel itself is optional. Internally it holds one structured representation of a calibration configuration — the parameter, observation, group, and prior-information tables, the control variables, model command lines, template and instruction pairs, and PEST++ options — and every command reads into or writes out of that representation, so one set of consistency rules applies whichever direction the data travels (Figure 1).

**`build`** reads calibration definitions from Excel worksheets or CSV files and writes a PEST-family control file. Parameter and observation tables may be distributed over many worksheets; spreadsheet columns that are not PEST fields — formulas, indices, notes — are ignored, which is what makes them harmless. Counts are calculated, never typed. Tied parameters, regularization equations generated from a preferred-value column, PEST_HP keywords, and PEST++ options are carried through as given. The build command can be stored in the workbook itself, so the executable configuration is regenerated with a single command.

**`validate`** is a report that changes nothing. Beyond the table checks — duplicate names, undefined groups, bad ties, initial values outside bounds, malformed or mistyped prior equations, PEST's name-length limits — it opens the template and instruction files and cross-checks them: every parameter cited somewhere, every observation read exactly once, no names the control file does not know. Optionally it runs each instruction file against the model's output with a small interpreter that follows the PEST manual, which catches the classic mistake of a whitespace instruction too few. It accepts a workbook directly, so a setup can be checked before any control file exists, and it exits with a nonzero status so a batch file can stop. It complements rather than replaces PEST's own checker.

**`dump`** is the reverse of `build`: it reads a control file into a workbook whose sheets `build` can read back. This is how an inherited control file enters the spreadsheet workflow, or how a lost workbook is recovered.

**`update`** returns results to an existing workbook. Given a parameter file, a residuals file, or PESTPP-IES parameter and observation ensembles (with a realization chosen by name or as the lowest-phi member of an iteration), it finds every worksheet with a parameter- or observation-name column, matches rows by name, and writes only the requested columns. Cells that hold formulas are left alone unless the user says otherwise. With residuals it also writes the objective function by observation group, as PEST reports it at the end of a run. Two backends exist: openpyxl, which needs no Excel, and xlwings, which drives Excel itself so that charts and macros survive and formulas recalculate.

**`parrep`** replaces PEST's PARREP utility — parameter values from a file or an ensemble realization into a new control file, optionally changing control variables on the way — and **`diff`** compares two control files, or a control file and a workbook, semantically: what was added, removed, or changed, column by column, with numbers compared to a tolerance. **`init`** writes a starter workbook that builds a valid control file as it is.

Two design decisions underpin auditability. Every command that produces a file writes a sidecar manifest beside it: the package version, the exact command line, the SHA-256 hash and sheets read from every input, and the hash and section counts of the output. A control file can therefore be traced to the precise workbook that made it. And round-tripping is defined semantically for supported content: reading a control file and writing it again preserves the represented calibration configuration, while formatting, name case, numeric representation, and some ordering are normalized; what is normalized and what is dropped (unrecognized sections, with a warning) is documented rather than discovered.

## Demonstration on a regional model

The demonstration uses the calibration workbook of a regional transient MODFLOW model from a consulting project (details withheld; all numbers are as reported by the software, and the script that produces them accompanies the release). makePst reads 19 sheets: control variables, parameter groups, eight parameter sheets (hydraulic and vertical conductivity, storage, specific yield, stream conductance, boundary heads, recharge multipliers, and miscellaneous), seven observation sheets (steady-state and transient heads, head differences, flows, leakage, and lake stages), an input/output sheet, and two PEST++ option sheets. Many observation weights are formulas that look up the number of records per well and a group-balancing factor.

*Build.* One command produces a 2.6-MB control file of 43,575 lines — 1,068 parameters in 12 groups, 41,747 observations in 12 groups, 185 regularization equations generated from the parameter sheets, 18 template and 7 instruction files — in about ten seconds on a laptop, most of it spent reading Excel. The manifest records the workbook's hash and the 19 sheet names.

*Round trip.* `dump` writes the control file to a fresh workbook; `build` from that workbook's stored command regenerates the control file; `diff` reports no semantic differences between the original and the rebuilt configuration. For this project the two makePst-generated files were also byte-identical.

*Comparison with the project's legacy conversion script.* `diff` between the control file the earlier script had produced for the same run and the new one reports 479 parameter values and 16,134 observation values changed at a relative tolerance of 10⁻⁹ and none at 10⁻⁵ — the six-significant-figure truncation — and one control variable, `JACUPDATE`, present only in the new file. This is not a benchmark against another software package; it illustrates the kind of configuration change that semantic comparison exposes in an evolving calibration workflow.

*Validation.* `makepst validate` on the built file in the project directory reports [outcome], and pestchek [version] reports [outcome] on the same file. [To be filled in from the project directory before submission.]

*Results back.* `update` with a parameter file and a residuals file writes values into the eight parameter sheets (1,068 rows matched) and modelled values and residuals into the seven observation sheets (41,747 rows), plus an objective-function sheet, leaving every weight formula untouched. [Add the xlwings result on the production workbook.]

**Table 1.** Round trip of the demonstration control file (wall-clock times on a laptop, Windows 11, Python 3.12).

| Step | Command | Time | Result |
|---|---|---|---|
| Workbook → control file | `makepst build` | 7–12 s | 1,068 par, 41,747 obs, 185 prior; 43,575 lines |
| Control file → workbook | `makepst dump` | 2–6 s | 9 sheets, incl. the build command |
| Workbook → control file | `makepst build` | 2–5 s | byte-identical to the original |
| Original vs rebuilt | `makepst diff` | ~1 s | no differences |
| Legacy script vs makePst | `makepst diff --rtol 1e-5` | ~1 s | 1 control variable (`JACUPDATE`) |
| Results → workbook copy | `makepst update` | 12–26 s | 1,068 + 41,747 rows; formulas untouched |

## Validation, scope, and limitations

At the archived release used here, the automated test suite contained [N] tests, run on Linux and Windows for Python 3.9 through 3.13 (pandas 2 and 3). They include golden-file builds from a synthetic workbook laid out like the demonstration's, read–write identity, `dump`-then-`build` equality, workbook updates with multi-sheet matching and formula protection, ensemble realization selection, every validation rule, the instruction interpreter, and the tutorial in the documentation, executed verbatim.

makePst reads and writes classic PEST control files, the PEST_HP extensions used in the demonstration, and PEST++ control files in both the classic and the version-2 external-table formats; it reads `.par`, `.res`/`.rei`, and PESTPP-IES ensemble and objective-function files. It does not perform calibration, uncertainty analysis, geostatistical parameterization, or run management. The instruction interpreter behind `validate` follows the manual but is not PEST, and its findings are reported as warnings; the documentation recommends running pestchek on every generated file. Sections makePst does not model are kept verbatim; anything unrecognized is dropped with a warning. Excel-faithful updates require Excel and xlwings; the openpyxl backend keeps macros but not charts, and formula results are stale until Excel next opens the file.

pyEMU provides a broader Python framework for PEST++ interface construction, parameterization, ensembles, geostatistics, and uncertainty analysis (White et al. 2016). makePst instead focuses on maintaining a bidirectional, auditable relationship between spreadsheet project records and executable PEST configurations. The packages are complementary: makePst-generated control files can enter pyEMU workflows, and PEST and PEST++ results can be returned to spreadsheets through makePst.

## Significance for practice

The immediate benefit is reproducibility: a calibration defined by a workbook and a one-line command can be rebuilt by another person on another machine and shown by `diff` to be the same, and the manifest makes that claim checkable years later, when a model is reviewed by a client or an agency. The second benefit is that the reviewed record and the executable file stop drifting apart. Modelers keep weighting in formulas, annotating in notes, and splitting parameters across sheets by type, and still obtain a control file whose name-level errors are caught before a run rather than after; results come back into the same workbook without a copy-and-paste step. Because CSV is accepted wherever a sheet is, the same workflow runs without Excel in a continuous-integration job or on a cluster.

By treating spreadsheets and control files as reproducibly linked representations of the same calibration configuration, makePst lets groundwater modelers retain familiar review practices while making control-file construction, checking, and result transfer reproducible. It is intended as a small, auditable layer within existing PEST and PEST++ workflows, not a replacement for any part of them.

## Software availability

makePst version [x.y.z], the release used for this article, is available under the MIT License at https://github.com/ougx/makePst (tagged `v[x.y.z]`) [and on PyPI as `makepst` — confirm at submission]. The repository contains a four-parameter tutorial that exercises every command, a synthetic workbook laid out like the demonstration's, and the script that produced the numbers in this article (`paper/reproduce.py`). The regional model's workbook is proprietary and not distributed.

## Acknowledgments

[Employer review; colleagues who tested; the PEST, PEST++, and pyEMU developers.]

## References

Doherty, J. 2015. *Calibration and Uncertainty Analysis for Complex Environmental Models.* Brisbane, Australia: Watermark Numerical Computing.

Ou, M. 2026. makePst: PEST control files from spreadsheet tables, and back (version [x.y.z]). https://github.com/ougx/makePst (accessed [date]).

White, J.T., M.N. Fienen, and J.E. Doherty. 2016. A python framework for environmental model uncertainty analysis. *Environmental Modelling & Software* 85: 217–228. https://doi.org/10.1016/j.envsoft.2016.08.017

White, J.T., R.J. Hunt, M.N. Fienen, and J.E. Doherty. 2020. *Approaches to Highly Parameterized Inversion: PEST++ Version 5, a Software Suite for Parameter Estimation, Uncertainty Analysis, Management Optimization and Sensitivity Analysis.* U.S. Geological Survey Techniques and Methods 7-C26. https://doi.org/10.3133/tm7C26

---

**Figure 1.** makePst workflow linking spreadsheet-based project records and PEST-family control files. Calibration definitions are built into and reconstructed from control files through a common structured representation; validation and semantic comparison support QA/QC, while parameter, residual, and ensemble results are returned to existing workbooks by name. Provenance manifests record software, commands, source hashes, output hashes, and project dimensions. [Figure file: `paper/figure1.svg`, generated by `paper/make_figure1.py`.]
