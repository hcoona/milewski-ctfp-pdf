# Feature Specification: Tree-sitter CST to Project AST Conversion

**Feature Branch**: `001-your-objective-is`  
**Created**: 2025-10-09  
**Status**: Draft  
**Input**: User description: "Your objective is to transform the S-expressions produced by tree-sitter parsing into a project-owned AST. This AST will feed later transformations such as macro expansion in the LaTeX preamble, converting the LaTeX AST into a general document AST, and rendering downstream formats like Asciidoc. These downstream tasks are informational only—you focus on the CST to AST conversion. You may use the Makefile to invoke the tree-sitter CLI for parsing and git ls-files to enumerate LaTeX sources under src so the Scheme code does not invoke tree-sitter directly."

> **Constitution Alignment**: Write every section in English. Define acceptance tests that map directly to
> Chez Scheme test suites that will be authored before implementation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Maintainer converts LaTeX CST to canonical AST (Priority: P1)

A repository maintainer selects a LaTeX source file tracked in the project, runs the conversion tool,
and receives a project-owned AST that adheres to the documented schema so downstream tooling can
consume it reliably.

**Why this priority**: Without a deterministic AST, none of the planned document transformations can
proceed. This is the foundational capability for all subsequent automation.

**Independent Test**: Execute the Chez Scheme test suite that parses a sample LaTeX file, compares the
produced AST against the expected schema snapshot, and confirms structural parity.

**Acceptance Scenarios**:

1. **Given** a LaTeX file under `src/` that tree-sitter can parse, **When** the maintainer runs the
   conversion workflow, **Then** a project-owned AST is emitted that matches the agreed schema and is
   stored in the designated output location.
2. **Given** a LaTeX file containing nested commands and environments, **When** conversion completes,
   **Then** the resulting AST preserves hierarchy, node attributes, and ordering required by downstream
   macro expansion tests.

---

### User Story 2 - Maintainer receives actionable feedback for parse failures (Priority: P2)

A maintainer attempts to convert a LaTeX file whose tree-sitter parse fails or produces incomplete
output and receives an actionable error report that identifies the file, failing node, and recommended
next step.

**Why this priority**: Timely, clear feedback prevents stalled pipelines and reduces manual debugging
time across the 200+ source files in the book.

**Independent Test**: Run the Chez Scheme error-handling tests that inject malformed CST fixtures and
assert the resulting diagnostics include file paths, failure reasons, and guidance for remediation.

**Acceptance Scenarios**:

1. **Given** a LaTeX file that tree-sitter cannot parse, **When** the maintainer triggers conversion,
   **Then** the tool aborts gracefully, logs the file path and parser error, and exits with a failure code
   consumed by automated tests.
2. **Given** tree-sitter produces a truncated CST, **When** the tool validates the structure, **Then** it
   rejects the output, flags the missing nodes, and suggests rerunning the Makefile target after fixing
   the LaTeX source.

---

### User Story 3 - Documentation build steward batches conversions (Priority: P3)

The documentation build steward batches conversions for all LaTeX files to refresh AST fixtures prior
to a release and verifies the batch completes within defined limits, producing a consolidated report of
successes and failures.

**Why this priority**: Batch conversion ensures downstream processing (macro expansion, format
rendering) uses synchronized ASTs, preventing regressions when multiple chapters change.

**Independent Test**: Execute the Chez Scheme batch-conversion tests that enumerate tracked LaTeX
files using repository metadata, run parallel conversions in a controlled sequence, and assert completion
within the time budget while capturing a machine-readable summary.

**Acceptance Scenarios**:

1. **Given** the repository contains all standard LaTeX sources, **When** the steward invokes the batch
   conversion entry point, **Then** the process converts every file, reports per-file status, and exits with
   a success code only if all files produce valid ASTs.
2. **Given** the batch encounters at least one failure, **When** processing finishes, **Then** the summary
   report lists the failed files with reasons and indicates the run failed so that CI can halt downstream
   jobs.

### Edge Cases

- Tree-sitter grammar updates introduce new node types that the AST schema does not yet recognize.
- LaTeX sources include custom macros or Unicode characters that tree-sitter treats as errors.
- Repository contains generated or temporary `.tex` files that should be excluded from conversion.
- Batch conversion exceeds predefined time limits due to extremely large chapters.
- File paths include spaces or special characters that disrupt automation tasks or reporting.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The workflow MUST enumerate all tracked LaTeX source files under `src/` using repository
  metadata so that transient files are excluded from conversion.
- **FR-002**: For each LaTeX source, the system MUST produce a project-owned AST that conforms to the
  documented node schema, preserving hierarchy, attributes, and ordering derived from the CST.
- **FR-003**: The system MUST emit deterministic diagnostics when conversion fails, including file path,
  failure classification (parse error, schema violation, I/O issue), and remediation guidance.
- **FR-004**: The workflow MUST support batch execution that processes the full document set within a
  single invocation and generates a machine-readable summary of outcomes for CI consumption.
- **FR-005**: The system MUST expose validation hooks that allow Chez Scheme unit tests to compare
  produced ASTs against expected fixtures without invoking external parsing logic.
- **FR-006**: The conversion MUST record the AST schema version alongside each output so downstream
  tooling can detect incompatible changes.

### Key Entities *(include if feature involves data)*

- **LaTeXSourceFile**: Identifies the path, chapter metadata, and checksum for a `.tex` document.
- **ConcreteSyntaxTree**: Represents the S-expression emitted by tree-sitter for a source file, including
  node types, spans, and textual content.
- **DocumentAST**: The canonical project-owned AST with normalized node names, attributes, schema
  version, and child ordering required for macro expansion and format transformations.
- **ConversionReport**: Captures batch execution metadata, per-file success/failure status, error
  diagnostics, and timing metrics.

## Assumptions

- Tree-sitter grammars for LaTeX are maintained and accessible via existing Makefile targets.
- Chez Scheme test harnesses can load fixture files containing CST and AST samples.
- Output AST artifacts will be stored in a repository-visible location governed by future planning tasks.
- Contributors have access to the Akku package manager to install any supporting Chez Scheme
  libraries needed for traversal utilities.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of tracked LaTeX source files convert to a valid AST in batch mode within 10 minutes
  on the CI reference machine.
- **SC-002**: 100% of conversion failures produce diagnostics containing file path, failure type, and next
  action, as verified by automated tests.
- **SC-003**: Manual review confirms the produced AST for a representative chapter preserves all node
  hierarchies and attributes required by downstream macro expansion, with no discrepancies found.
- **SC-004**: Batch conversion summary exports a machine-readable report that downstream jobs consume
  without additional transformation, evidenced by successful integration test execution.
