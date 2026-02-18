-- RLS policies for all tenant-scoped tables.
-- App sets per-request: SET LOCAL app.tenant_id = '<uuid>'

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_role_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON users;
CREATE POLICY tenant_isolation ON users
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON roles;
CREATE POLICY tenant_isolation ON roles
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON user_role_assignments;
CREATE POLICY tenant_isolation ON user_role_assignments
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON refresh_tokens;
CREATE POLICY tenant_isolation ON refresh_tokens
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON audit_log;
CREATE POLICY tenant_isolation ON audit_log
    USING (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::uuid
    )
    WITH CHECK (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::uuid
    );

-- Sprint 2 RLS
ALTER TABLE project_sequences ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE incoming_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE incoming_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON project_sequences;
CREATE POLICY tenant_isolation ON project_sequences
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON projects;
CREATE POLICY tenant_isolation ON projects
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON message_threads;
CREATE POLICY tenant_isolation ON message_threads
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON incoming_messages;
CREATE POLICY tenant_isolation ON incoming_messages
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON incoming_attachments;
CREATE POLICY tenant_isolation ON incoming_attachments
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON tasks;
CREATE POLICY tenant_isolation ON tasks
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Sprint 3 RLS
ALTER TABLE files ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE incident_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE nonconformances ENABLE ROW LEVEL SECURITY;
ALTER TABLE capa_actions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON files;
CREATE POLICY tenant_isolation ON files
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON file_links;
CREATE POLICY tenant_isolation ON file_links
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON incidents;
CREATE POLICY tenant_isolation ON incidents
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON incident_messages;
CREATE POLICY tenant_isolation ON incident_messages
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON nonconformances;
CREATE POLICY tenant_isolation ON nonconformances
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON capa_actions;
CREATE POLICY tenant_isolation ON capa_actions
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Sprint 4 RLS
ALTER TABLE doc_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE doc_template_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_docs ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_doc_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ack_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE ack_responses ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON doc_templates;
CREATE POLICY tenant_isolation ON doc_templates
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON doc_template_versions;
CREATE POLICY tenant_isolation ON doc_template_versions
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON project_docs;
CREATE POLICY tenant_isolation ON project_docs
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON project_doc_versions;
CREATE POLICY tenant_isolation ON project_doc_versions
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON ack_requests;
CREATE POLICY tenant_isolation ON ack_requests
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON ack_responses;
CREATE POLICY tenant_isolation ON ack_responses
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Sprint 5 RLS
ALTER TABLE checklist_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE checklist_template_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_checklist_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_checklist_template_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE checklist_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON checklist_templates;
CREATE POLICY tenant_isolation ON checklist_templates
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON checklist_template_versions;
CREATE POLICY tenant_isolation ON checklist_template_versions
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON project_checklist_templates;
CREATE POLICY tenant_isolation ON project_checklist_templates
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON project_checklist_template_versions;
CREATE POLICY tenant_isolation ON project_checklist_template_versions
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON checklist_runs;
CREATE POLICY tenant_isolation ON checklist_runs
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Sprint 6 RLS
ALTER TABLE drawings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON drawings;
CREATE POLICY tenant_isolation ON drawings
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Hardening patch v1 – files + file_links RLS
ALTER TABLE files ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_links ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON files;
CREATE POLICY tenant_isolation ON files
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON file_links;
CREATE POLICY tenant_isolation ON file_links
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Sprint 7 RLS
ALTER TABLE timesheets ENABLE ROW LEVEL SECURITY;
ALTER TABLE time_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_export_lines ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON timesheets;
CREATE POLICY tenant_isolation ON timesheets
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON time_entries;
CREATE POLICY tenant_isolation ON time_entries
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON compliance_rules;
CREATE POLICY tenant_isolation ON compliance_rules
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON compliance_results;
CREATE POLICY tenant_isolation ON compliance_results
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON payroll_exports;
CREATE POLICY tenant_isolation ON payroll_exports
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON payroll_export_lines;
CREATE POLICY tenant_isolation ON payroll_export_lines
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
