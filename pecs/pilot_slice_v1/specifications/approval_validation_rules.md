# Approval Validation Rules

`Approval` is the only stored confirmation fact. BriefVersion and TransformationSpecVersion contain neither `is_approved` nor `approved_at`.

## Brief
Valid only when target type/order/version/hash match the current Brief and both context fields are null. Otherwise stage is `BRIEF_PENDING`.

## TransformationSpec
Valid only when target type/order/version/hash match, context Brief id/hash equal the selected approved Brief, and the spec itself references the same Brief id/hash. Otherwise stage is `TRANSFORMATION_PENDING`.

## Atomic APPROVED
`READY_FOR_APPROVAL -> APPROVED` is one transaction after both schemas, both hashes and both compatible immutable Approval facts pass. Then `approval_stage=COMPLETE` and Execute is enabled.

Changing Brief invalidates Brief-derived approval and all dependent spec approvals. Changing only spec preserves the valid Brief approval. Approval rows are immutable and duplicates are forbidden.
