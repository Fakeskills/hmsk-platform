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
