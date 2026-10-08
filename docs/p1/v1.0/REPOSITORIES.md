# Repository Contracts

Repository methods below are contracts, not implementation code. All write methods participate in a caller-owned Unit of Work and never commit independently.

## Common persistence-boundary rule

Any method that appends a P0 contract document must validate it using the unchanged validated P0 schema/hash rules before issuing the DB write. Exact-reference checks are required both in repository logic for useful errors and in DB constraints/guards where `SQLITE_SCHEMA.md` requires defense in depth.

## OrderRepository

Responsibilities:

- create an Order record;
- get by id;
- list basic order summaries;
- update editable order metadata;
- persist selected Brief/TransformationSpec references;
- persist status/approval_stage only when instructed by a higher-level domain use case.

Selected version ids must resolve to versions belonging to the same Order. P1 does not require the two selected versions to be mutually compatible in every intermediate workflow state; exact compatibility is checked by the later approval workflow before `APPROVED`.

P1 does not embed the P3 approval state machine in this repository. It supports compare-and-set semantics (`expected current state`) so later domain logic cannot silently overwrite stale state, even in a single-user Streamlit process with reruns.

## InputAssetRepository

Responsibilities:

- register one durable local payload metadata record through the file+DB protocol;
- get by id;
- list assets for an order;
- verify that referenced file path remains inside workspace.

No method parses CSV/XLSX or produces previews.

## BriefVersionRepository

Responsibilities:

- validate against P0 BriefVersion schema, verify JSON/index identity and recompute P0 content hash before append;
- append a version;
- get exact version id;
- list versions for an order in version order;
- fetch latest version number;
- provide a verified/trust-boundary load that repeats schema/index/hash checks.

No update-in-place method exists. A changed Brief is a new version.

## TransformationSpecVersionRepository

Same append/get/list/trust-boundary semantics as BriefVersionRepository plus exact stored Brief id/order/hash validation. No update-in-place method exists.

## ApprovalRepository

Responsibilities:

- append an immutable Approval only after validating the complete P0 Approval contract;
- require target version existence in the same order and exact target hash equality;
- for Transformation Approval, require exact target TransformationSpec hash plus context Brief id/hash equal to that spec's stored Brief context;
- find valid Approval for a Brief version + recalculated content hash;
- find valid Approval for a TransformationSpec version + recalculated spec hash + exact Brief id/hash context;
- list approvals for an order.

There are no update or delete methods. DB insertion guards repeat exact-target/context checks to prevent raw-SQL bypass.

## ExecutionRunRepository

Responsibilities:

- append a run record only when the Brief and TransformationSpec belong to the same order and the spec points to that exact Brief id/hash;
- require `brief_approval_id` to be a valid exact BRIEF Approval for the run Brief;
- require `transformation_approval_id` to be a valid exact TRANSFORMATION_SPEC Approval for the run spec and the same run Brief context;
- get/list runs;
- persist only mutable run fields (`status`, `finished_at`, `metrics`, `error`) as later stages progress.

Order/version/Approval reference fields are immutable after insert. DB guards repeat the exact-reference checks. P1 tests repository persistence only; P1 does not start or execute runs.

## ArtifactRepository

Responsibilities:

- register a newly promoted immutable artifact path/checksum through the file+DB Unit of Work protocol;
- get by id;
- list artifacts for a run.

No overwrite operation is provided.

## QAReportRepository

Responsibilities:

- validate a supplied report against the P0 QAReport schema;
- derive/verify indexed fields against `report_json`;
- require the report run/version tuple to equal the referenced ExecutionRun tuple;
- append a QAReport record;
- get/list reports by run;
- provide verified/trust-boundary load checks.

No QA computation exists here.

## EventLogRepository

Responsibilities:

- append event;
- if `run_id` is non-null, require the run belongs to the same order;
- list events in chronological order for an order/run.

No update/delete operations exist.

## Repository invariants

- repositories do not accept absolute filesystem paths;
- repositories do not expose raw SQL to UI/domain callers;
- repository methods do not perform network access;
- repository methods do not invoke ingestion, transformation, QA computation or LLM code;
- no repository silently creates or modifies an Approval-derived boolean;
- immutable records are append-only;
- all lookups are order-scoped where cross-order confusion is possible;
- public storage errors conform to the unchanged P0 error schema.
