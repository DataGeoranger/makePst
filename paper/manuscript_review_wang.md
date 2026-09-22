# Manuscript review and proposed revisions: workbook-centered calibration review

Reviewed version: `e86c11c` (makePst 0.3.0), on the local `paper-edits` branch. This review responds to Zhaowei Wang's experience using makePst alongside pyEMU. It is an editorial review supported by the manuscript, repository documentation, and relevant implementation; it does not independently reproduce the reported regional-model results.

## Main finding

The manuscript already discusses all five points, but the emphasis is uneven. Formula-based weighting and complementarity with pyEMU are explicit. Keeping source context, calibration inputs, and PEST/PEST++ settings together for review is distributed across several sections. The main opportunity is to make this combined practical benefit the organizing message, while retaining the existing evidence for reproducibility and auditability.

Suggested central message: makePst complements pyEMU by giving project teams a shared workbook in which to review parameter and observation data, their source context, weighting formulas, and control settings, then build a reproducible PEST configuration from the reviewed values.

## Coverage of Wang's points

Line numbers below refer to Michael's [original manuscript at the reviewed commit](https://github.com/ougx/makePst/blob/e86c11c/paper/manuscript.md).

| Point from practical use | Current coverage | Assessment and proposed improvement |
|---|---|---|
| A useful complement to pyEMU | Opening, line 16; scope, line 75. The scope paragraph explicitly calls the packages complementary and describes exchange through control files and results. | Already explicit. Explain the practical division of work earlier: pyEMU supports scripting and analysis; makePst supports the team's workbook-based review and exchange workflow. Acknowledge that pyEMU also supports observation reweighting. |
| Parameter and observation inputs organized in one spreadsheet | Opening, line 14; software description, lines 26–30; regional demonstration, line 48. The demonstration identifies eight parameter sheets and seven observation sheets in one workbook. | Strong coverage of the organization, weaker explanation of why it helps review. Describe one workbook with multiple worksheets as a shared calibration record. Avoid implying that every model input file is embedded in Excel. |
| Source data visible alongside calibration decisions | Opening, line 14, mentions observation sheets by data source, helper columns, and annotations. The demonstration lists observation types. | Partly explicit. Explain that values, source references, native values, and data-selection notes can remain alongside the PEST fields. This is a capability of the workbook organization, not automatic reconstruction or verification of original data provenance. |
| Weights set and revised directly through spreadsheet equations | Opening, line 14; `update`, line 36; demonstration, lines 48 and 56; limitations, line 73; significance, line 79. | Already strong, particularly formula preservation and the regional example's record counts and balancing factors. Add the complete sequence: revise formulas or factors → recalculate and save → rebuild. Clarify that formulas in required PEST fields supply calculated values; they are not simply ignored. |
| PEST/PEST++ settings reviewed and control files generated in the same place | Software description, lines 26–30; demonstration, line 48, includes control variables and two PEST++ option sheets. | Technically present but the review benefit is implicit. Connect the settings sheets to the parameter and observation tables, so readers understand they can review the configuration together before building it. |

## Proposed editing plan

1. **Replace the second and third opening paragraphs.** Introduce the workbook as a shared review record containing values, source context, formulas, and settings. Position makePst positively alongside pyEMU, including pyEMU's existing reweighting capability.
2. **Replace the `build` paragraph.** Explain the joint organization of tables and settings. Distinguish helper columns omitted from the control file from formula-derived values used in required fields. Describe the recalculate–save–build sequence.
3. **Keep the current demonstration and Table 1.** They already supply a concrete example of many sheets, weighting formulas, and returned results. No new timings, counts, calibration outcomes, or claims about Wang's project are needed for this revision.
4. **Refine the scope paragraphs.** Correct the cached-value warning claim and describe a practical pyEMU handoff with a concise compatibility qualification.
5. **Replace the first significance paragraph with two short paragraphs.** Lead with the shared review experience, then explain the reproducibility benefit. State that the workbook organizes calibration tables and settings while external model, template, and instruction files remain linked separately.
6. **Review length before submission.** The local counting method gives 2,105 body words for the original manuscript and 2,191 for the revised manuscript (+86). Full-file counts are 2,447 and 2,533, respectively, including front matter, references, and the figure caption. These are editorial counts, not a verified journal calculation. The existing plan targets a shorter body; if necessary, trim repeated command descriptions rather than removing the new practical explanation.

The revisions are incorporated directly into [manuscript.md](manuscript.md), using the original manuscript filename so the pull request shows the changes in place. The separate draft file has been removed; `plan.md` remains unchanged. The title, author list, impact statement, demonstration, table, references, and figure caption are retained.

## Proposed replacement wording

The following excerpts are reproduced from the candidate draft so the main revisions can be reviewed separately.

### Opening: shared calibration record

For such applications, control files are rarely practical to maintain manually, and in many consulting workflows the working calibration record is instead kept in spreadsheets. A workbook can bring parameter definitions, observation values, source references, weighting formulas, and PEST/PEST++ settings into one reviewable record. Sheets can separate parameter types and observation sources, while helper columns retain model layer or pilot-point indices, native values, and notes on data selection. Formulas can balance observation groups, down-weight a period of record, or scale a parameter bound from a native value. This organization lets colleagues review the calibration inputs alongside the assumptions used to prepare them; the control file is derived from that record.

### Opening: complement to pyEMU

pyEMU (White et al. 2016) supports scripted parameterization, control-file construction, and observation reweighting. makePst complements these capabilities for teams that also review calibration decisions in spreadsheets. Source references, formulas, and annotations remain visible alongside the parameter and observation tables, allowing colleagues to inspect the setup without tracing the supporting scripts. The workbook becomes a shared interface for reviewing calibration decisions, linked reproducibly to the executable control file.

### What makePst does: build

**`build`** reads Excel worksheets or CSV files and writes a PEST-family control file. Parameter and observation tables may span worksheets, alongside control variables, PEST++ options, and model input/output mappings. Helper columns containing source references, indices, or notes remain in the workbook but are excluded from the control file. Formula-derived PEST fields, including observation weights, are read from saved calculated values; `build` does not evaluate formulas. Modelers can revise weighting formulas or their inputs, recalculate and save the workbook, then rebuild the control file. Counts are calculated automatically; tied parameters, regularization equations generated from preferred values, and PEST_HP keywords are supported. The build command can be stored in the workbook itself.

### Scope: pyEMU handoff

pyEMU provides a broader Python framework for PEST++ interface construction, parameterization, ensembles, geostatistics, and uncertainty analysis (White et al. 2016). A complementary workflow uses pyEMU for interface construction and analysis, and makePst for reviewing calibration tables, weighting formulas, and control settings together in a workbook. Supported control-file content provides the exchange between the packages, while makePst returns PEST and PEST++ results to the workbook. Interchange is subject to each package's format support; it should not be assumed to preserve every specialized control setting.

### Significance for practice: replacement opening paragraphs

The immediate practical benefit is a shared place to review the calibration setup: parameter definitions, observation values and source references, weighting assumptions, and PEST/PEST++ settings can be inspected together. A modeler can revise a weighting factor, review the recalculated weights alongside the observations, and rebuild the control file from the saved workbook. Results return by name for the next review cycle, with existing weight formulas protected by default. This keeps the reasoning behind a configuration close to the values supplied to PEST.

The same workflow supports reproducibility. A workbook and its build command can regenerate a configuration, `diff` can check semantic agreement, and manifests record which files produced each output. The workbook centralizes calibration tables and settings; model files, templates, and instruction files remain separate, linked through the input/output mappings. CSV input also supports automated workflows where a spreadsheet interface is unnecessary.

## Technical checks behind the wording

- **Formula handling:** [makepst/excel.py](https://github.com/ougx/makePst/blob/e86c11c/makepst/excel.py#L21) reads workbook tables and checks for missing cached formula results. Its warning explicitly states that existing cached values may be stale and their freshness cannot be determined. The original manuscript's statement that `build` warns when values are missing *or stale* is too broad. The candidate now distinguishes missing-value warnings from undetectable stale values.
- **Formula preservation and recalculation:** [README.md](https://github.com/ougx/makePst/blob/e86c11c/README.md#L209) documents default formula protection; its backend discussion at line 235 distinguishes Excel/xlwings recalculation from openpyxl updates. The candidate does not claim that preserving formula text guarantees current calculated values.
- **Centralized settings and source context:** [README.md](https://github.com/ougx/makePst/blob/e86c11c/README.md#L162) documents control variables, parameter/observation fields, optional helper columns, input/output mappings, and PEST++ option tables. Source references and notes are proposed workbook content, not a newly claimed makePst data-import or data-quality feature. A workbook hash identifies a file; it does not validate the scientific origin of its observations.
- **Fair positioning of pyEMU:** The [official pyEMU repository](https://github.com/pypest/pyemu#what-is-pyemu) explicitly lists control-file manipulation, observation processing, and observation reweighting. The distinctive practical emphasis here is workbook-centered review and exchange, not a claim that pyEMU cannot manage weights or tables.
- **Interchange limitations:** [makePst's bridge documentation](https://github.com/ougx/makePst/blob/e86c11c/README.md#L516) describes the existing `to_pyemu`/`from_pyemu` bridge and settings that may change or be lost. [tests/test_pyemu.py](https://github.com/ougx/makePst/blob/e86c11c/tests/test_pyemu.py#L20) contains relevant tests. These were inspected, not rerun. The manuscript draft uses a general compatibility qualification rather than adding unverified interoperability results.

## Optional evidence to strengthen a later revision

A cropped workbook illustration could make Wang's point more concrete than additional prose. It could show an observation value, its source reference, a weighting factor, the weight formula and calculated weight, together with the relevant parameter and settings tabs. Use an actual, shareable workbook excerpt and confirm its contents before describing it as part of the regional demonstration. A second figure is optional; the current revision is supportable without one.

If a worked weight-change example is added later, document the actual starting factor, revised factor, recalculation step, resulting control-file weights, and semantic comparison. Do not present an invented formula as the regional project's weighting method or imply that a workflow demonstration establishes better calibration performance.

## Other observations for the authors

Two nearby issues deserve a separate factual check before submission:

- The earlier [paper/plan.md](https://github.com/ougx/makePst/blob/e86c11c/paper/plan.md) still lists version-2 external tables as unsupported, whereas the current manuscript and repository documentation describe support. Use the current manuscript and implementation for this revision rather than copying limitations from that older outline.
- [paper/reproduce.py](https://github.com/ougx/makePst/blob/e86c11c/paper/reproduce.py#L60) creates synthetic parameter and residual files for its openpyxl update demonstration (parameter values multiplied by 1.01 and residuals fixed at -0.5). The authors should distinguish that reproducible transfer check from the separately reported production-workbook update. The proposed draft retains the existing numerical claims and does not recast synthetic data as observed calibration results.

The proposed wording is now incorporated into `manuscript.md` for review through the pull request. This companion review records the rationale and outstanding factual checks; Michael's original text remains available in Git history.
