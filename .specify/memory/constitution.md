<!--
Sync Impact Report
- Version change: 1.1.0 → 1.2.0
- Modified principles: VI. Nanopass Transformations (added source location retention)
- Added sections: None
- Removed sections: None
- Templates requiring updates:
  ✅ .specify/templates/plan-template.md
  ✅ .specify/templates/spec-template.md
  ✅ .specify/templates/tasks-template.md
  ⚠ commands directory missing → no command templates to update
- Follow-up TODOs: None
-->

# Category Theory for Programmers PDF Constitution

## Core Principles

### I. English-Language Documentation
All documentation, specifications, commit descriptions, and code comments MUST be written in
English. Maintain consistent terminology so reviews, translation, and archiving stay reliable.
Rationale: English-only artifacts keep collaboration clear across tooling, community, and the
source material.

### II. Owned Abstract Syntax Trees
Tree-sitter outputs MAY be used only as raw concrete syntax trees. Contributors MUST translate
them into project-owned abstract syntax trees before any analysis, mutation, or code generation.
Rationale: A maintained AST boundary grants stability against upstream parser changes and keeps
domain semantics explicit.

### III. Test-First Delivery
For every change, write failing automated tests before implementing functional code. Reject any
merge where implementation precedes its covering tests. Rationale: Test-first work preserves the
book build integrity and guards against regressions in the PDF pipeline.

### IV. Chez Scheme Exclusivity
All executable tooling, automation, and scripts MUST be authored in Chez Scheme. When external
utilities are unavoidable, wrap them behind Chez Scheme entry points so the workflow remains
uniform. Rationale: A single language keeps runtime environments reproducible across contributors.

### V. External Package Leverage
Prefer existing, community-vetted Chez Scheme libraries via the Akku package manager before writing
custom implementations. Identify gaps explicitly when no package exists and seek maintainers for
guidance. Rationale: Reusing proven libraries accelerates delivery and concentrates effort on the
book domain.

### VI. Nanopass Transformations
Implement every CST or AST transformation by leveraging the nanopass framework. Each pass MUST focus
on a single, tightly scoped rewrite that touches only the most relevant portion of the tree, while
propagating precise source location metadata into resulting nodes. Reject work that batches unrelated
changes into one pass or drops location tracking. Rationale: Fine-grained nanopass stages keep
transformations auditable and reduce regression risk.

## Implementation Constraints

- Transform every tree-sitter CST into a dedicated AST module per feature before downstream use.
- Author CST and AST transformations as nanopass passes that only adjust the smallest relevant tree
  fragments per pass.
- Preserve source location metadata through every CST and AST rewrite so diagnostics map back to the
  originating files.
- Preserve English-language standards in LaTeX sources and any generated artifacts.
- Record Akku dependencies in `Akku.manifest` and lock upgrades through `Akku.lock`.
- Provide Chez Scheme entry points for build automation, ensuring tests orchestrate any scripts.

## Workflow Quality Gates

1. Open with a constitution check in plans: confirm language, AST boundaries, test coverage strategy,
   Chez Scheme ownership, and dependency reuse.
2. Author tests in Chez Scheme and demonstrate they fail before implementation work starts.
3. Implement functionality strictly after the failing tests exist, keeping commits reviewable.
4. During reviews, verify that any new dependency references an Akku package or documents the lack
  of a suitable alternative.
5. Confirm that every CST/AST rewrite plan enumerates the nanopass stages needed, each with a
  single-focus scope.
6. Inspect nanopass designs for explicit strategies that retain or improve source location metadata
  across passes.
7. Block merges when any quality gate fails until corrective commits restore compliance.

## Governance

- Adoption: This constitution governs all engineering and documentation practices within the
  Category Theory for Programmers PDF project.
- Amendments: Proposals require a written diff, explicit impact assessment, and approval from at
  least two maintainers. Accepted amendments set a new version and amendment date.
- Versioning: Increment `MAJOR.MINOR.PATCH` according to impact—MAJOR for incompatible policy
  shifts, MINOR for new principles or substantial expansions, PATCH for clarifications.
- Compliance Review: Before merging, reviewers MUST confirm adherence to principles, gates, and
  tooling constraints, logging deviations and remediation steps.

**Version**: 1.2.0 | **Ratified**: 2025-10-09 | **Last Amended**: 2025-10-09
