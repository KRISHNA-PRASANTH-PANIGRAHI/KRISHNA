-- Private backend persistence for ClassGuard. Auth stays in Supabase Auth.

CREATE ROLE classguard_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 10;

CREATE SCHEMA classguard AUTHORIZATION postgres;

REVOKE ALL ON SCHEMA classguard FROM PUBLIC, anon, authenticated;

GRANT USAGE ON SCHEMA classguard TO classguard_app;

GRANT CONNECT ON DATABASE postgres TO classguard_app;

ALTER ROLE classguard_app SET search_path = pg_catalog;

ALTER ROLE classguard_app SET statement_timeout = '15s';

ALTER ROLE classguard_app SET idle_in_transaction_session_timeout = '30s';

CREATE TABLE classguard.account_identities (
	user_id UUID NOT NULL,
	email VARCHAR(254),
	PRIMARY KEY (user_id)
);

ALTER TABLE classguard.account_identities OWNER TO postgres;

REVOKE ALL ON TABLE classguard.account_identities FROM PUBLIC, anon, authenticated;

ALTER TABLE classguard.account_identities ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE classguard.account_identities TO classguard_app;

CREATE POLICY backend_access ON classguard.account_identities FOR ALL TO classguard_app USING (true) WITH CHECK (true);

CREATE TABLE classguard.institutions (
	id UUID NOT NULL,
	name VARCHAR(160) NOT NULL,
	active BOOLEAN NOT NULL,
	PRIMARY KEY (id)
);

ALTER TABLE classguard.institutions OWNER TO postgres;

REVOKE ALL ON TABLE classguard.institutions FROM PUBLIC, anon, authenticated;

ALTER TABLE classguard.institutions ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE classguard.institutions TO classguard_app;

CREATE POLICY backend_access ON classguard.institutions FOR ALL TO classguard_app USING (true) WITH CHECK (true);

CREATE TABLE classguard.memberships (
	institution_id UUID NOT NULL,
	user_id UUID NOT NULL,
	role VARCHAR(20) NOT NULL,
	active BOOLEAN NOT NULL,
	PRIMARY KEY (institution_id, user_id),
	FOREIGN KEY(institution_id) REFERENCES classguard.institutions (id),
	CONSTRAINT membership_role CHECK (role IN ('admin', 'teacher', 'student'))
);

ALTER TABLE classguard.memberships OWNER TO postgres;

REVOKE ALL ON TABLE classguard.memberships FROM PUBLIC, anon, authenticated;

ALTER TABLE classguard.memberships ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE classguard.memberships TO classguard_app;

CREATE POLICY backend_access ON classguard.memberships FOR ALL TO classguard_app USING (true) WITH CHECK (true);

CREATE TABLE classguard.classrooms (
	id UUID NOT NULL,
	institution_id UUID NOT NULL,
	title VARCHAR(160) NOT NULL,
	subject VARCHAR(100) NOT NULL,
	description VARCHAR(2000) NOT NULL,
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
	duration_minutes INTEGER NOT NULL,
	created_by UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT class_duration CHECK (duration_minutes >= 5 AND duration_minutes <= 480),
	FOREIGN KEY(institution_id, created_by) REFERENCES classguard.memberships (institution_id, user_id),
	UNIQUE (id, institution_id),
	FOREIGN KEY(institution_id) REFERENCES classguard.institutions (id)
);

CREATE INDEX ix_classguard_classrooms_created_by ON classguard.classrooms (created_by);

CREATE INDEX ix_classguard_classrooms_institution_id ON classguard.classrooms (institution_id);

ALTER TABLE classguard.classrooms OWNER TO postgres;

REVOKE ALL ON TABLE classguard.classrooms FROM PUBLIC, anon, authenticated;

ALTER TABLE classguard.classrooms ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE classguard.classrooms TO classguard_app;

CREATE POLICY backend_access ON classguard.classrooms FOR ALL TO classguard_app USING (true) WITH CHECK (true);

CREATE TABLE classguard.invitations (
	id UUID NOT NULL,
	institution_id UUID NOT NULL,
	email VARCHAR(254) NOT NULL,
	role VARCHAR(20) NOT NULL,
	token_hash VARCHAR(64) NOT NULL,
	created_by UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	accepted_at TIMESTAMP WITH TIME ZONE,
	revoked_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	UNIQUE (token_hash),
	FOREIGN KEY(institution_id, created_by) REFERENCES classguard.memberships (institution_id, user_id),
	FOREIGN KEY(institution_id) REFERENCES classguard.institutions (id),
	CONSTRAINT invitation_role CHECK (role IN ('teacher', 'student'))
);

CREATE INDEX ix_classguard_invitations_institution_id ON classguard.invitations (institution_id);

CREATE UNIQUE INDEX one_outstanding_invitation_per_email ON classguard.invitations (institution_id, email) WHERE accepted_at IS NULL AND revoked_at IS NULL;

ALTER TABLE classguard.invitations OWNER TO postgres;

REVOKE ALL ON TABLE classguard.invitations FROM PUBLIC, anon, authenticated;

ALTER TABLE classguard.invitations ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE classguard.invitations TO classguard_app;

CREATE POLICY backend_access ON classguard.invitations FOR ALL TO classguard_app USING (true) WITH CHECK (true);

CREATE TABLE classguard.enrollments (
	classroom_id UUID NOT NULL,
	institution_id UUID NOT NULL,
	user_id UUID NOT NULL,
	PRIMARY KEY (classroom_id, institution_id, user_id),
	FOREIGN KEY(classroom_id, institution_id) REFERENCES classguard.classrooms (id, institution_id),
	FOREIGN KEY(institution_id, user_id) REFERENCES classguard.memberships (institution_id, user_id)
);

ALTER TABLE classguard.enrollments OWNER TO postgres;

REVOKE ALL ON TABLE classguard.enrollments FROM PUBLIC, anon, authenticated;

ALTER TABLE classguard.enrollments ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE classguard.enrollments TO classguard_app;

CREATE POLICY backend_access ON classguard.enrollments FOR ALL TO classguard_app USING (true) WITH CHECK (true);

CREATE INDEX ix_memberships_user_id ON classguard.memberships (user_id);

CREATE INDEX ix_enrollments_institution_user ON classguard.enrollments (institution_id, user_id);

CREATE INDEX ix_invitations_institution_creator ON classguard.invitations (institution_id, created_by);
