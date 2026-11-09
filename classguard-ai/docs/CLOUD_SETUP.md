# Supabase cloud setup

The configured local installation uses Supabase Auth and PostgreSQL for the existing onboarding features. The web app and FastAPI service still run on this computer; this is not a hosted web deployment or a live-video integration.

## Database access

`infra/sql/classguard_cloud_schema.sql` contains the schema applied through the recorded Supabase migration `classguard_private_backend_schema`. It creates the six application tables in the private `classguard` schema, preserves the composite foreign keys and invitation uniqueness rule, and adds indexes for membership and enrollment lookups.

Tables are owned by the migration administrator. The `classguard_app` runtime role has schema usage and table select/insert/update/delete permissions. It has no schema creation, role management, database creation, replication, superuser or RLS-bypass privileges. Browser `anon` and `authenticated` roles receive no access to the private schema.

RLS is enabled on all six tables. Its policies allow the backend role to operate on application records; these are **not tenant-isolation policies within that role**. Tenant, membership and classroom authorization remain enforced by the FastAPI application. Do not expose this database credential to a browser or use it as a general administration credential.

The API uses the shared session pooler on port 5432, SQLAlchemy schema translation, and a small application pool (three persistent connections with at most two overflow connections). TLS uses certificate and hostname verification (`sslmode=verify-full`). The CA file in `infra/certificates/supabase-prod-ca-2021.crt` came from [Supabase's certificate download](https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt). Follow the current [connection documentation](https://supabase.com/docs/guides/database/connecting-to-postgres) when configuring another project.

## Local configuration and startup

The API reads its private `apps/api/.env`; the browser reads only the public API URL and Supabase publishable settings from `apps/web/.env.local`. Both files are ignored by Git. For a new checkout, copy the example files only when the private files do not already exist.

Set `DATABASE_SCHEMA=classguard` alongside a PostgreSQL `DATABASE_URL` that includes the session-pooler username, generated backend password, `sslmode=verify-full`, `sslrootcert` pointing to the certificate file, and a connection timeout. URL-encode credentials and certificate paths, or construct the URL using SQLAlchemy's `URL.create()`. Keep the generated password out of migration files and repository history.

Double-click `Start ClassGuard.cmd` to launch both services. Alternatively, run:

```powershell
.\scripts\start-local.ps1 -NoBrowser
.\scripts\start-local.ps1 -CheckOnly
```

Open `http://localhost:3000/setup`. The launcher preserves existing environment files and records. Its database initialization only creates missing tables; it is not a migration runner. Apply future cloud schema changes with a privileged migration operator, not the runtime account.

Private setup records and first-login information are stored under the ignored `out/cloud-setup` folder on the configured computer. They are deliberately absent from GitHub.

## Verification on 2026-11-09

- Both local services cold-started successfully through the launcher.
- The configured PostgreSQL connection authenticated as `classguard_app` with `sslmode=verify-full` and found all six application tables.
- The runtime role's superuser, database-creation, role-creation, replication and RLS-bypass flags were all false.
- Direct reads of `auth.users` and attempts to create a table in `classguard` were denied with PostgreSQL permission errors.
- An ORM transaction inserted related records across all six tables, read them back, preserved timezone-aware timestamps, performed an update, and rolled back successfully. No validation records were retained.
- The administrator signup exists, but the provider still reported **Email not confirmed** during the real password-login test. The provider's `email_confirmed_at` remained empty. No successful administrator login or institution creation is claimed by this check.

Complete the provider's email confirmation before signing in. If the original link has expired, request a fresh signup-confirmation email. Once signed in, the existing **Create institution** flow creates an administrator membership through the authenticated API.

Live video, media admission, attendance collection, recording, AI features, public hosting and production operations remain separate implementation milestones.
