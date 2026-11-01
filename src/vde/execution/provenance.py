"""Bounded immutable execution facts; never dataset QA assertions."""


def snapshot(plan):
    return dict(asset_id=plan.asset.id, source_byte_sha256=plan.asset.byte_sha256,
                input_selection=plan.handoff.input_selection,
                brief_content_hash=plan.brief.content_hash,
                transformation_content_hash=plan.spec.content_hash)


def summarize(plan, table, row_count, checksum, budget, warnings):
    return dict(format_revision='P4_INTERNAL_V2', dataset_id=plan.dataset_id,
                columns=list(table.columns), row_count=row_count, logical_result_checksum=checksum,
                operation_audit=table.audit, source=snapshot(plan),
                resources=budget.summary(), warnings=warnings)
