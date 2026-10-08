# P1 Scope

## In scope

P1 establishes the durable local substrate for Pilot Slice V1:

- one Python application and one local Streamlit entry point;
- SQLite metadata database;
- local filesystem workspace for input and artifact bytes;
- persistence for Order, InputAsset, BriefVersion, TransformationSpecVersion, Approval, ExecutionRun, Artifact, QAReport and EventLog;
- migration tracking and startup schema checks;
- repository interfaces and Unit of Work boundary;
- exact-reference integrity between persisted entities;
- P0 JSON Schema/content-hash validation at persistence trust boundaries;
- storage/path/checksum responsibilities;
- restart-safe persistence and storage reconciliation;
- structured mapping of persistence/workspace failures to the unchanged P0 error model;
- tests proving data survives process restart and that P0 approval/hash/reference invariants are not weakened by persistence.

## Not in scope

The following are deliberately absent from P1:

- reading or parsing CSV/XLSX content;
- selecting XLSX sheets;
- input schema preview;
- detecting encodings/delimiters;
- creating Brief/TransformationSpec through UI;
- implementing approval actions or READY_FOR_APPROVAL -> APPROVED business workflow;
- executing any transformation operation;
- export and round-trip validation;
- deterministic QA computation;
- LLM analysis/review/invocations;
- URL, JSON, HTML or API ingestion;
- Telegram or marketplace actions;
- browser automation;
- workers, queues, FastAPI or separate backend services.

P1 may validate an already supplied P0 contract document before persisting it. That is persistence-boundary validation, not P3 authoring/workflow logic and not QA execution.

## Persistence boundary

SQLite stores metadata and authoritative structured contract documents. Dataset rows and table contents are never normalized into generic SQLite row tables. Source/result/intermediate bytes live in the local filesystem workspace.

## P1 interpretation of later-stage entities

ExecutionRun, Artifact and QAReport tables exist in P1 because they are part of the approved durable model and must survive restart. P1 does not create them from an execution/QA workflow; tests may persist validated fixture records directly through repositories.

SourceDefinition and LLMInvocation are intentionally not separate P1 persistence tables. SourceDefinition network configuration is outside the Pilot P1 roadmap and Pilot uses one local InputAsset; LLMInvocation is inapplicable because Pilot has no LLM.
