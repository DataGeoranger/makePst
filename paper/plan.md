# Groundwater Technology Spotlight: Editor Inquiry and Manuscript Skeleton

## Editor Inquiry

**To:** Ken Bradbury, Editor-in-Chief, *Groundwater* (`ken.bradbury@wisc.edu`)
**Subject:** Technology Spotlight inquiry: makePst spreadsheet workflow for PEST control files

Dear Dr. Bradbury,

I am writing to ask whether an article about **makePst**, an open-source Python tool for bidirectional exchange between spreadsheet tables and PEST-family control files, would be suitable for the *Groundwater* Technology Spotlight column.

Groundwater model calibration projects commonly maintain parameter definitions, observation data, control settings, and model input/output mappings in spreadsheets. In practice, modelers heavily rely on Excel formulas to dynamically calculate observation weights, balance weighting between different observation groups, or scale parameter bounds. Translating these dynamic tables into a static PEST, PEST++, or PEST_HP control file can involve substantial manual formatting and consistency checking. Results must then be transferred back into project workbooks for review and reporting. These steps become difficult to audit in highly parameterized models and can easily overwrite or break the modeler's embedded formula logic.

makePst provides a reproducible workflow for building control files from Excel or CSV tables, reading existing control files into structured workbooks, and updating those workbooks with parameter and residual results. It computes section counts, validates parameter groups and tied parameters, constructs and checks regularization equations, preserves supported control settings and PEST++ options, and handles PESTPP-IES parameter and observation ensembles. A PARREP-style command can also produce a new control file from a selected realization.

The proposed contribution is distinct from, and complementary to, pyEMU. pyEMU provides comprehensive Python support for constructing PEST++ interfaces, parameterization, ensembles, and uncertainty analysis. Although pyEMU can read and write control files and tabular data, makePst treats the spreadsheet as a first-class, bidirectional project interface: it can reconstruct a rebuildable workbook from an existing control file and update matching rows across multiple worksheets from PEST and PESTPP-IES outputs without replacing formula cells. When Microsoft Excel and the optional xlwings backend are available, workbook formulas, macros, charts, and other Excel features are preserved during updates. These operations are exposed through a reusable command-line workflow and do not require project-specific Python scripts. makePst is therefore intended as an interchange and round-tripping layer that can be used alongside pyEMU, not as a replacement for it.

The proposed article would demonstrate the workflow using a groundwater calibration example with 1,068 parameters and 41,747 observations. The example would show reproducible construction of a control file, semantic round-tripping through an Excel workbook, validation of the generated file, and transfer of calibration results back to the workbook. One figure would summarize the bidirectional workflow, and a second would show the workbook organization or validation results.

The proposed title is:

> **makePst: A Reproducible Spreadsheet Workflow for PEST Model Calibration**

The manuscript would follow the Technology Spotlight format: no abstract, approximately 2,300 words, one or two figures, and no more than five references. The source code, automated tests, and documentation are publicly available at [github.com/ougx/makePst](https://github.com/ougx/makePst). A small reproducible example and a versioned, archived software release with a DOI would accompany the manuscript. Known format limitations would be stated explicitly.

Would this topic be appropriate for consideration as a Technology Spotlight article in *Groundwater*?

Sincerely,

Michael Ou
**[Affiliation]**
**[Postal address]**
ougengxin@gmail.com
**[ORCID]**

---

## Manuscript Skeleton

### Working Title

**makePst: A Reproducible Spreadsheet Workflow for PEST Model Calibration**

### Article Impact Statement

**Draft, 127 characters:** makePst links spreadsheets and PEST control files to make groundwater model calibration easier to reproduce, audit, and update.

### Target Format

- Technology Spotlight, *Groundwater*
- Approximately 2,000 to 2,300 words
- No abstract
- One or two figures
- No more than five literature citations
- Public software repository, versioned release, and data/software availability statement

### 1. The Practical Problem (250-350 words)

**Purpose:** Establish a groundwater-practice problem rather than a software-development problem.

- Introduce PEST-family software as widely used for groundwater model calibration and uncertainty analysis.
- Explain that project configuration is often assembled and reviewed in spreadsheets, while execution requires rigidly structured control files.
- Emphasize that modelers heavily use Excel formulas to calculate and balance weights across observation groups or scale parameters dynamically.
- Describe the risks of manual transfer: incorrect counts, inconsistent groups, invalid tied parameters, and results copied into the wrong rows that overwrite and destroy formula logic.
- Explain why these risks grow with highly parameterized models and distributed project teams.
- State the unmet need: a transparent and reproducible bridge between tabular project records and executable PEST configurations.

**Candidate opening:**

> Groundwater model calibration often spans two representations of the same project: spreadsheets used by modelers to organize and review calibration data, and text-based control files used by PEST-family software. Maintaining consistency between these representations becomes increasingly difficult as the number of parameters, observations, regularization equations, and model files grows.

### 2. The makePst Workflow (450-550 words)

**Purpose:** Explain what the software does and what is distinctive about it.

- Introduce makePst as an open-source Python package and command-line application.
- Describe the central structured `Pst` data model.
- Present the four user workflows:
  - `build`: Excel/CSV tables to a control file.
  - `dump`: a control file to a rebuildable workbook.
  - `update`: parameter, residual, or ensemble results to an existing workbook.
  - `parrep`: selected parameter values or an IES realization to a new control file.
- Explain computed counts and consistency validation.
- Describe supported regularization, tied parameters, PEST_HP fields, and PEST++ options.
- Emphasize that result updates leave existing formula cells untouched; with Excel and xlwings, macros, charts, and other workbook features are also preserved.
- Position makePst relative to pyEMU: focused interchange, round-tripping, and formula-aware workbook updates versus broad interface construction and uncertainty analysis.

**Figure 1:** Bidirectional workflow diagram showing Excel/CSV tables, the makePst data model, PEST control files, PEST/PEST++ execution, and PAR/RES/REI/IES results returning to the workbook.

### 3. Demonstration with a Groundwater Calibration Project (500-650 words)

**Purpose:** Show practical scale, reproducibility, and usefulness without turning the article into a case-study report.

- Briefly describe the groundwater model and calibration context without disclosing sensitive project information.
- Report the example scale:
  - **[verified parameter count; currently approximately 1,068]**
  - **[verified observation count; currently approximately 41,747]**
  - **[parameter-group count]**
  - **[template/instruction-file counts]**
- Explain workbook organization: CONTROL, PARGP, split PAR and OBS sheets, IO, PEST++ options, and comments.
- Demonstrate deterministic construction of the control file.
- Dump the resulting file to a new workbook and rebuild it.
- Compare the original and rebuilt files semantically.
- Run `pestchek` and report the exact outcome.
- Update a copy of the workbook from a `.par` and `.res`/`.rei` file.
- Demonstrate selection of a PESTPP-IES realization, if space permits.

**Evidence to collect before drafting:**

- Exact model dimensions and generated file size.
- Runtime for build, dump, and update on a stated computer.
- `pestchek` version and output.
- Automated-test count and supported Python/platform matrix.
- Semantic comparison results and any expected formatting differences.

**Figure 2:** Either a cropped workbook view showing the structured sheets and returned results, or a compact validation table comparing source and rebuilt project dimensions.

### 4. Validation, Scope, and Limitations (300-400 words)

**Purpose:** Establish trust and avoid overstating compatibility.

- Summarize automated unit and integration tests.
- Describe golden-file and build-dump-rebuild testing.
- State that generated files should also be checked with the applicable PEST utility.
- List supported control-file sections and result formats concisely.
- State current limitations explicitly:
  - PEST++ version-2 external-table control files are not currently supported.
  - Observation-group covariance references are not retained **[revise if implemented]**.
  - Unknown sections may be reported but not preserved **[revise if implemented]**.
  - Excel-faithful updates require Excel and the optional xlwings dependency.
- Explain that makePst does not perform calibration, uncertainty analysis, geostatistical parameterization, or worker management.

### 5. Practical Significance (200-300 words)

**Purpose:** Close on groundwater practice rather than code features.

- Explain how rebuildable workbooks improve review by modelers, clients, regulators, and collaborators.
- Highlight traceability between calibration definitions and executable files.
- Discuss reduced manual transfer and easier incorporation of calibration results.
- Note that plain CSV input supports automated and non-Excel workflows.
- Identify likely users: consulting modelers, agencies, researchers, and educators using PEST-family software.

**Candidate closing:**

> By treating spreadsheets and control files as synchronized views of the same calibration configuration, makePst enables groundwater modelers to retain familiar review practices while making control-file construction and result transfer reproducible. The software is intended to provide a small, auditable layer within existing PEST and PEST++ workflows.

### Software and Data Availability

> makePst version **[version]** is available under the MIT License at [https://github.com/ougx/makePst](https://github.com/ougx/makePst). The archived version used in this article is available at **[DOI]**. A compact reproducible example and the commands used to generate the reported results are provided at **[example/archive URL]**. The larger groundwater project data are **[publicly available at ... / unavailable because ..., with a synthetic example supplied instead]**.

### Acknowledgments

- **[Funding, employer review, project collaborators, and testers]**
- **[PEST/PEST++ and pyEMU developers, where appropriate]**

### Conflict of Interest

> The author declares **[no conflicts of interest / relevant interests]**.

### Candidate References (Maximum Five)

Select only references actually used in the final text:

1. A primary PEST or PEST++ reference.
2. The primary pyEMU paper or current software citation.
3. A reference on highly parameterized groundwater model calibration or regularization.
4. The archived makePst software release and DOI.
5. One directly relevant groundwater software-workflow reference, if needed.

### Pre-Submission Checklist

- [ ] Add external `pestchek` validation to the example workflow.
- [ ] Publish a versioned release.
- [ ] Archive that release and obtain a DOI.
- [ ] Provide a small public example with expected outputs.
- [ ] Confirm the repository and installation instructions from a clean environment.
- [ ] Document supported features and round-trip limitations.
- [ ] Confirm all model dimensions and performance numbers.
- [ ] Obtain employer/client approval for any project details or screenshots.
- [ ] Add author affiliation, postal address, ORCID, funding, and acknowledgments.
- [ ] Confirm the Article Impact Statement is no more than 140 characters.
- [ ] Keep the manuscript within approximately 2,300 words and five references.
