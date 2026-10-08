-- Immutable P1 baseline; forward-only migrations.
CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY CHECK(version>0),
    name TEXT NOT NULL CHECK(length(name)>0),
    checksum TEXT NOT NULL CHECK(length(checksum)=64 AND checksum NOT GLOB '*[^0-9a-f]*'),
    applied_at TEXT NOT NULL
);
CREATE TABLE orders (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id)>0),
    title TEXT NOT NULL,
    listing_text TEXT NOT NULL,
    listing_url TEXT,
    status TEXT NOT NULL CHECK(status IN ('DRAFT','ANALYZING','NEEDS_CLARIFICATION','READY_FOR_APPROVAL','APPROVED','EXECUTING','NEEDS_FIX','READY','FAILED','CANCELLED')),
    approval_stage TEXT CHECK(approval_stage IN ('BRIEF_PENDING','TRANSFORMATION_PENDING','COMPLETE')),
    selected_brief_version_id TEXT,
    selected_transformation_spec_version_id TEXT,
    budget TEXT,
    deadline TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(selected_brief_version_id,id) REFERENCES brief_versions(id,order_id),
    FOREIGN KEY(selected_transformation_spec_version_id,id) REFERENCES transformation_spec_versions(id,order_id)
);
CREATE TABLE input_assets (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id)>0),
    order_id TEXT NOT NULL REFERENCES orders(id),
    original_filename TEXT NOT NULL,
    workspace_relpath TEXT NOT NULL UNIQUE CHECK(length(workspace_relpath)>0 AND substr(workspace_relpath,1,1)<>'/' AND instr(workspace_relpath,char(92))=0 AND instr(workspace_relpath,':')=0 AND instr(workspace_relpath,char(0))=0 AND instr('/'||workspace_relpath||'/','/../')=0 AND instr('/'||workspace_relpath||'/','/./')=0 AND instr(workspace_relpath,'//')=0 AND substr(workspace_relpath,-1)<>'/'),
    media_type TEXT,
    size_bytes INTEGER NOT NULL CHECK(typeof(size_bytes)='integer' AND size_bytes>=0),
    byte_sha256 TEXT NOT NULL CHECK(length(byte_sha256)=64 AND byte_sha256 NOT GLOB '*[^0-9a-f]*'),
    created_at TEXT NOT NULL
);
CREATE TABLE brief_versions (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id)>0),
    order_id TEXT NOT NULL REFERENCES orders(id),
    version_number INTEGER NOT NULL CHECK(typeof(version_number)='integer' AND version_number>0),
    schema_version TEXT NOT NULL CHECK(schema_version='1.1'),
    content_hash TEXT NOT NULL CHECK(length(content_hash)=64 AND content_hash NOT GLOB '*[^0-9a-f]*'),
    document_json TEXT NOT NULL CHECK(document_json IS NULL OR json_valid(document_json)),
    created_at TEXT NOT NULL,
    UNIQUE(order_id,version_number),
    UNIQUE(id,order_id),
    UNIQUE(id,order_id,content_hash)
);
CREATE TABLE transformation_spec_versions (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id)>0),
    order_id TEXT NOT NULL REFERENCES orders(id),
    version_number INTEGER NOT NULL CHECK(typeof(version_number)='integer' AND version_number>0),
    schema_version TEXT NOT NULL CHECK(schema_version='1.1'),
    content_hash TEXT NOT NULL CHECK(length(content_hash)=64 AND content_hash NOT GLOB '*[^0-9a-f]*'),
    document_json TEXT NOT NULL CHECK(document_json IS NULL OR json_valid(document_json)),
    created_at TEXT NOT NULL,
    brief_version_id TEXT NOT NULL,
    brief_content_hash TEXT NOT NULL CHECK(length(brief_content_hash)=64 AND brief_content_hash NOT GLOB '*[^0-9a-f]*'),
    UNIQUE(order_id,version_number),
    UNIQUE(id,order_id),
    UNIQUE(id,order_id,content_hash),
    FOREIGN KEY(brief_version_id,order_id,brief_content_hash) REFERENCES brief_versions(id,order_id,content_hash)
);
CREATE TABLE approvals (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id)>0),
    order_id TEXT NOT NULL REFERENCES orders(id),
    target_type TEXT NOT NULL CHECK(target_type IN ('BRIEF','TRANSFORMATION_SPEC')),
    target_version_id TEXT NOT NULL,
    target_content_hash TEXT NOT NULL CHECK(length(target_content_hash)=64 AND target_content_hash NOT GLOB '*[^0-9a-f]*'),
    context_brief_version_id TEXT,
    context_brief_content_hash TEXT CHECK(length(context_brief_content_hash)=64 AND context_brief_content_hash NOT GLOB '*[^0-9a-f]*'),
    approved_by TEXT NOT NULL CHECK(approved_by='local_user'),
    approved_at TEXT NOT NULL,
    CHECK((target_type='BRIEF' AND context_brief_version_id IS NULL AND context_brief_content_hash IS NULL) OR (target_type='TRANSFORMATION_SPEC' AND context_brief_version_id IS NOT NULL AND context_brief_content_hash IS NOT NULL))
);
CREATE UNIQUE INDEX approvals_brief_exact ON approvals(target_type,target_version_id,target_content_hash) WHERE target_type='BRIEF';
CREATE UNIQUE INDEX approvals_spec_exact ON approvals(target_type,target_version_id,target_content_hash,context_brief_version_id,context_brief_content_hash) WHERE target_type='TRANSFORMATION_SPEC';
CREATE TABLE execution_runs (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id)>0),
    order_id TEXT NOT NULL REFERENCES orders(id),
    brief_version_id TEXT NOT NULL,
    brief_approval_id TEXT NOT NULL REFERENCES approvals(id),
    transformation_spec_version_id TEXT NOT NULL,
    transformation_approval_id TEXT NOT NULL REFERENCES approvals(id),
    status TEXT NOT NULL CHECK(status IN ('running','succeeded','needs_fix','failed','cancelled')),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    input_snapshot_json TEXT NOT NULL CHECK(input_snapshot_json IS NULL OR json_valid(input_snapshot_json)),
    metrics_json TEXT NOT NULL CHECK(metrics_json IS NULL OR json_valid(metrics_json)),
    error_json TEXT CHECK(error_json IS NULL OR json_valid(error_json)),
    UNIQUE(id,order_id),
    UNIQUE(id,brief_version_id,transformation_spec_version_id),
    FOREIGN KEY(brief_version_id,order_id) REFERENCES brief_versions(id,order_id),
    FOREIGN KEY(transformation_spec_version_id,order_id) REFERENCES transformation_spec_versions(id,order_id)
);
CREATE TABLE artifacts (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id)>0),
    run_id TEXT NOT NULL REFERENCES execution_runs(id),
    artifact_type TEXT NOT NULL CHECK(length(artifact_type)>0),
    format TEXT NOT NULL CHECK(length(format)>0),
    workspace_relpath TEXT NOT NULL UNIQUE CHECK(length(workspace_relpath)>0 AND substr(workspace_relpath,1,1)<>'/' AND instr(workspace_relpath,char(92))=0 AND instr(workspace_relpath,':')=0 AND instr(workspace_relpath,char(0))=0 AND instr('/'||workspace_relpath||'/','/../')=0 AND instr('/'||workspace_relpath||'/','/./')=0 AND instr(workspace_relpath,'//')=0 AND substr(workspace_relpath,-1)<>'/'),
    checksum TEXT NOT NULL CHECK(length(checksum)=64 AND checksum NOT GLOB '*[^0-9a-f]*'),
    created_at TEXT NOT NULL
);
CREATE TABLE qa_reports (
    report_id TEXT PRIMARY KEY NOT NULL,
    run_id TEXT NOT NULL,
    brief_version_id TEXT NOT NULL,
    transformation_spec_version_id TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    overall_status TEXT NOT NULL CHECK(overall_status IN ('PASS','PASS_WITH_WARNINGS','FAIL')),
    report_json TEXT NOT NULL CHECK(report_json IS NULL OR json_valid(report_json)),
    FOREIGN KEY(run_id,brief_version_id,transformation_spec_version_id) REFERENCES execution_runs(id,brief_version_id,transformation_spec_version_id)
);
CREATE TABLE event_log (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id)>0),
    order_id TEXT NOT NULL REFERENCES orders(id),
    run_id TEXT,
    event_type TEXT NOT NULL CHECK(length(event_type)>0),
    payload_json TEXT CHECK(payload_json IS NULL OR json_valid(payload_json)),
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id,order_id) REFERENCES execution_runs(id,order_id)
);
CREATE TRIGGER approval_exact BEFORE INSERT ON approvals BEGIN
    SELECT CASE WHEN NEW.target_type='BRIEF' AND NOT EXISTS (
        SELECT 1 FROM brief_versions b WHERE b.id=NEW.target_version_id
        AND b.order_id=NEW.order_id AND b.content_hash=NEW.target_content_hash
    ) THEN RAISE(ABORT,'Approval Brief target mismatch') END;
    SELECT CASE WHEN NEW.target_type='TRANSFORMATION_SPEC' AND NOT EXISTS (
        SELECT 1 FROM transformation_spec_versions s JOIN brief_versions b
        ON (b.id,b.order_id,b.content_hash)=(s.brief_version_id,s.order_id,s.brief_content_hash)
        WHERE s.id=NEW.target_version_id AND s.order_id=NEW.order_id AND s.content_hash=NEW.target_content_hash
        AND s.brief_version_id=NEW.context_brief_version_id AND s.brief_content_hash=NEW.context_brief_content_hash
    ) THEN RAISE(ABORT,'Approval spec target/context mismatch') END;
END;
CREATE TRIGGER run_exact BEFORE INSERT ON execution_runs BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM brief_versions b JOIN transformation_spec_versions s
        ON (s.brief_version_id,s.order_id,s.brief_content_hash)=(b.id,b.order_id,b.content_hash)
        JOIN approvals ba ON ba.id=NEW.brief_approval_id AND ba.target_type='BRIEF'
        AND (ba.order_id,ba.target_version_id,ba.target_content_hash)=(b.order_id,b.id,b.content_hash)
        AND ba.context_brief_version_id IS NULL AND ba.context_brief_content_hash IS NULL
        JOIN approvals sa ON sa.id=NEW.transformation_approval_id AND sa.target_type='TRANSFORMATION_SPEC'
        AND (sa.order_id,sa.target_version_id,sa.target_content_hash)=(s.order_id,s.id,s.content_hash)
        AND (sa.context_brief_version_id,sa.context_brief_content_hash)=(b.id,b.content_hash)
        WHERE b.id=NEW.brief_version_id AND s.id=NEW.transformation_spec_version_id AND b.order_id=NEW.order_id
    ) THEN RAISE(ABORT,'ExecutionRun exact references mismatch') END;
END;
CREATE TRIGGER run_identity_immutable BEFORE UPDATE ON execution_runs WHEN
    NEW.id IS NOT OLD.id OR NEW.order_id IS NOT OLD.order_id OR
    NEW.brief_version_id IS NOT OLD.brief_version_id OR NEW.brief_approval_id IS NOT OLD.brief_approval_id OR
    NEW.transformation_spec_version_id IS NOT OLD.transformation_spec_version_id OR
    NEW.transformation_approval_id IS NOT OLD.transformation_approval_id OR
    NEW.started_at IS NOT OLD.started_at OR NEW.input_snapshot_json IS NOT OLD.input_snapshot_json
BEGIN SELECT RAISE(ABORT,'ExecutionRun identity is immutable'); END;
CREATE TRIGGER approvals_update_immutable BEFORE UPDATE ON approvals BEGIN SELECT RAISE(ABORT,'Immutable record'); END;
CREATE TRIGGER approvals_delete_immutable BEFORE DELETE ON approvals BEGIN SELECT RAISE(ABORT,'Immutable record'); END;
CREATE TRIGGER event_log_update_immutable BEFORE UPDATE ON event_log BEGIN SELECT RAISE(ABORT,'Immutable record'); END;
CREATE TRIGGER event_log_delete_immutable BEFORE DELETE ON event_log BEGIN SELECT RAISE(ABORT,'Immutable record'); END;
CREATE INDEX input_assets_lookup ON input_assets(order_id);
CREATE INDEX brief_versions_lookup ON brief_versions(order_id,version_number);
CREATE INDEX transformation_spec_versions_lookup ON transformation_spec_versions(order_id,version_number);
CREATE INDEX approvals_lookup ON approvals(order_id);
CREATE INDEX execution_runs_lookup ON execution_runs(order_id,started_at);
CREATE INDEX artifacts_lookup ON artifacts(run_id);
CREATE INDEX qa_reports_lookup ON qa_reports(run_id,generated_at);
CREATE INDEX event_log_lookup ON event_log(order_id,created_at,id);
