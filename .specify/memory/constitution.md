<!--
Sync Impact Report
===================
Version change: template → 1.0.0

Bump rationale: Initial ratification. Adapted from the shared five-principle governance
framework and retargeted to the domain of this project: a real-time data analytics and
monitoring system built with FastAPI (REST + WebSocket), Streamlit, and MariaDB 11.7
accessed exclusively through the SQLAlchemy ORM, deployed via Docker Compose. Principle
framework (Code Quality, Testing, UX Consistency, Performance, Language & Documentation)
is preserved; domain-specific clauses, rationales, and performance targets are rewritten
for this project, including the hard requirement that all database access use the ORM
(no raw SQL).

Modified principles: all five retargeted to the realtime-monitoring domain.
Added sections: none (same structure: Additional Constraints, Workflow, Governance)
Removed sections: none
Follow-up TODOs: none

Note: This Sync Impact Report is temporary scratch for amendment review and may be
removed before committing the constitution file.
-->

# Real-Time Data Analytics & Monitoring System Constitution

## Core Principles

### I. Code Quality

Code quality is a non-negotiable baseline. All code merged into the main branch MUST pass
automated static checks (linter, formatter, type checker) with no errors; warnings MUST be
resolved before merge or explicitly documented with a justified waiver. Every module MUST have a
single, clear responsibility (auth, data CRUD, analytics, realtime generator/WebSocket, admin),
and every public API MUST be defined with Pydantic schemas documenting purpose, inputs, outputs,
and error behavior, surfaced through Swagger. All database access MUST go through the SQLAlchemy
ORM; raw SQL strings are PROHIBITED. Commented-out dead code, leftover debug output, and unused
dependencies MUST NOT be committed. All dependencies MUST be declared with pinned versions, and
any new dependency MUST be evaluated for maintenance status, license, and security before
adoption.

**Rationale**: The system handles authentication, role-based access, and persisted records; low-
quality code or ad-hoc raw SQL directly causes security holes, data corruption, and
unmaintainable behavior.

### II. Testing Standards

Testing is a delivery requirement, not an option. Core backend logic (JWT issuance/validation,
role-based permission checks, CRUD ownership rules, analytics aggregation, anomaly thresholding)
MUST have unit tests covering authorized and unauthorized paths and boundary conditions. Cross-
component behavior — REST endpoints via an async test client, WebSocket push, batch write of
realtime data to MariaDB, CSV/JSON import — MUST have integration tests against a disposable test
database using the ORM. Any bug-fix commit MUST first add a test that reproduces the bug. The test
suite on the main branch MUST pass in full before merge, and line coverage for the auth and
data/analytics modules MUST be ≥ 80%.

**Rationale**: Permission and data-integrity defects carry high cost; only repeatable tests keep
authorization rules and analytics correct across changes.

### III. UX Consistency

User-facing surfaces (Streamlit pages: login, realtime monitor, data management, analytics, admin)
MUST maintain consistent terminology, layout, and interaction patterns. Authentication state MUST
be managed consistently in session state, with uniform login/logout behavior and clear handling of
expired tokens. Charts (line, bar, trend) MUST share consistent axes, units, time zone (default
Asia/Taipei), and timestamp format (ISO 8601), and anomalies MUST be marked with a consistent
visual cue. Error and empty states MUST provide clear, actionable messages and MUST NOT expose raw
stack traces or internal error codes to end users. Interfaces MUST meet baseline accessibility
(keyboard operability, sufficient contrast, icons paired with text where meaning is conveyed).

**Rationale**: Operators must read live data and act quickly; a consistent, clear experience
reduces misjudgment and response delay.

### IV. Performance Requirements

The system MUST meet measurable performance targets. A standard REST read endpoint MUST respond in
≤ 300 ms (P95) under nominal load, excluding cold start. Realtime data generated each second MUST
be pushed to connected WebSocket clients with ≤ 1 s end-to-end latency (P95). Realtime data MUST be
persisted to MariaDB via periodic or condition-triggered batch writes rather than one INSERT per
event, and the batch policy MUST be configurable. The database layer MUST use async access
(asyncmy) with a bounded SQLAlchemy connection pool, and MUST degrade gracefully (retry with
backoff) during transient database unavailability rather than crashing the service. Every
performance target MUST have a corresponding metric or log and MUST be verifiable.

**Rationale**: "Real-time" is the system's core value; excessive latency or per-event writes
negate the monitoring purpose and overload the database.

### V. Language & Documentation

This constitution document MUST be authored in English. All other artifacts — specifications
(spec), plans (plan), tasks (tasks), user-facing documentation (README), UI copy, and API
descriptions — MUST be written in Traditional Chinese (zh-TW). Code identifiers and technical
keywords MAY remain in English, but their accompanying documentation MUST follow the applicable
language rule for its artifact type. Documentation MUST be kept in sync with the implementation:
the README MUST cover project intro, tech stack, local run steps, Docker deployment commands, the
Swagger API docs link, and seed test accounts; a commit that changes interface or behavior without
updating the corresponding documentation MUST be treated as incomplete.

**Rationale**: The operating team works in Traditional Chinese, so delivered artifacts use zh-TW;
the constitution is kept in English as a stable, portable governance reference.

## Additional Constraints & Compliance

- Persistence: MariaDB 11.7 MUST be the datastore, accessed exclusively through the SQLAlchemy ORM
  with Alembic-managed migrations; raw SQL is PROHIBITED.
- Authentication & authorization: JWT-based authentication is mandatory, with three roles (Admin,
  User, Viewer) and enforced permissions (e.g. update/delete limited to the record owner or Admin;
  user/log/db-status management limited to Admin).
- Security: Passwords MUST be stored hashed (never plaintext); secrets (JWT key, DB credentials)
  MUST come from environment variables and MUST NOT be committed; a `.env.example` MUST be
  provided without real secrets.
- Containerization: The system MUST run via Docker Compose with multi-stage Dockerfiles, inter-
  container networking, a persistent volume for MariaDB, and environment-variable configuration.
- Observability: Errors MUST be handled explicitly and system activity logged; Admin MUST be able
  to query system logs, database status, and realtime history.
- Deliverables: The repository MUST include complete code, README, `.env.example`, at least one
  sample CSV for import, and a system architecture diagram.

## Development Workflow & Quality Gates

- Every change MUST go through code review, and the reviewer MUST confirm conformance with each
  principle of this constitution, explicitly checking that no raw SQL was introduced.
- Pre-merge gates: static checks pass, tests green, coverage target met, Alembic migrations present
  for schema changes, documentation updated in the language required for its artifact type.
- Any complexity that deviates from the principles MUST be explicitly justified in the PR
  description; unjustified complexity MUST be rejected.
- Security-sensitive changes (authentication, authorization, database access, WebSocket exposure,
  environment/secret handling) MUST be flagged and MUST state what was verified.

## Governance

This constitution supersedes other development conventions; where a convention conflicts with this
constitution, this constitution prevails.
Amendment procedure: Any amendment MUST be proposed in writing, stating the change, rationale, and
impact, and takes effect only after approval by the project owner.
Versioning policy (semantic versioning):
- MAJOR: Removal or redefinition of existing governance clauses/principles (backward incompatible).
- MINOR: Addition of a principle or section, or material expansion of existing guidance.
- PATCH: Wording clarifications, typo fixes, and other non-semantic refinements.

Compliance review: All PRs and reviews MUST verify conformance with this constitution; at least
quarterly, the principles MUST be reviewed for continued applicability. When an amendment takes
effect, the version number and amendment date MUST be updated and dependent templates and
documentation synced as needed.

**Version**: 1.0.0 | **Ratified**: 2026-10-22 | **Last Amended**: 2026-10-22
