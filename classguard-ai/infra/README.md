# Infrastructure boundary

Fresh checkouts use SQLite and loopback development servers. The configured development workspace uses Supabase PostgreSQL through its session pooler. Provider credentials are supplied through ignored application environment files.

`sql/classguard_cloud_schema.sql` defines the private `classguard` schema, its six application tables, indexes and backend-only access policies. Tables remain owned by the migration operator; the runtime role has data access without ownership, role-management rights or `BYPASSRLS`. FastAPI membership checks enforce institution boundaries. This role's RLS policies do not independently isolate tenants inside the backend.

`certificates/supabase-prod-ca-2021.crt` is a public CA certificate downloaded from Supabase's distribution endpoint, `https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt`. The configured database connection uses `sslmode=verify-full` to verify the certificate chain and hostname. The certificate is public material, not a private key.

See `../docs/CLOUD_SETUP.md` for setup and validation. The schema template deliberately creates a `NOLOGIN` runtime role. A trusted operator assigns its password separately; credentials must not be recorded in schema migrations or source control.

Before the first institutional pilot, provision and validate:

- PostgreSQL with a migration history, restricted credentials, backups and a tested restore procedure.
- Supabase Auth with the chosen account onboarding policy, email delivery and asymmetric JWT signing.
- LiveKit Cloud or an authorized self-hosted LiveKit deployment with HTTPS/WSS, TURN reachability and a tested removal/rejoin policy.
- A Node-capable frontend host and an API/container host with explicit CORS origins.
- Protected storage and a worker queue when files, exports or AI processing are introduced.

The development Supabase project has been configured. Frontend/API public hosting, LiveKit, backup/restore acceptance and production operations remain pending. Select concurrency targets and budget before configuring those services.
