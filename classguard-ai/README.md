# ClassGuard AI

A responsive online classroom application for schools, colleges and coaching institutes. This repository implements the first stages of the supplied PRD. The current version is the **0.2 development build**, including institution onboarding and enrollment.

## Project documents

- `ClassGuard_AI_PRD_v1.0.pdf` preserves the supplied 11-page specification.
- `ClassGuard_AI_PRD_v1.1.pdf` adds engineering definitions and acceptance criteria with corrected layout.
- `docs/ARCHITECTURE.md` records implementation decisions and integration boundaries.
- `docs/IMPLEMENTATION_PLAN.md` defines milestones and release evidence.
- `docs/OPEN_SOURCE_REVIEW.md` verifies the proposed reference repositories and their observed licenses.
- `docs/SECURITY_REVIEW.md` records the local attack tests, fixes and remaining deployment gaps.
- `docs/CLOUD_SETUP.md` describes the Supabase database connection and its verified limits.

## Included in this build

- Responsive Next.js/React/TypeScript dashboard, class planner, people directory, invitation acceptance, attendance overview and setup views.
- Supabase email/password sign-in integration, enabled by environment configuration.
- FastAPI API with verified JWT identity, database membership checks and institution-scoped class routes.
- SQLite local-development persistence with PostgreSQL-compatible SQLAlchemy models.
- Optional private PostgreSQL schema, restricted backend credentials and a bounded connection pool.
- Signed-in institution creation with administrator membership.
- Administrator-created teacher/student invitations, seven-day expiry, manual link sharing and revocation.
- Member activation and teacher/student role management, with administrator memberships protected from these edits.
- Class enrollment and removal for administrators and the teacher who owns the class.
- CLI provisioning for trusted local operators.
- Attendance interval calculation with overlap merging, actual teaching windows, break exclusion, UTC normalization and uncertainty handling.
- Unit and authorization tests for the API and attendance rules.
- Web app manifest and app icon foundation.

The explicitly labeled UI preview uses local example data. Configured sign-in and the API use real records. Live video, waiting-room admission, attendance event collection, polls, recording, AI summaries and production operations are subsequent milestones. The attendance calculator is implemented independently of the future media-event pipeline.

## Start locally on Windows

Double-click **Start ClassGuard.cmd** to prepare and start both applications, check their health and open the setup page. The launcher preserves existing environment files and database records, reuses this project's healthy services, and rebuilds/restarts them when their source or configuration changes. Other applications using ports 3000 or 8000 are left alone. Background service logs are saved under the ignored `out/local-run` folder. The services remain running until Windows closes them or the computer restarts; double-click the launcher again when needed.

For a read-only readiness check, run `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local.ps1 -CheckOnly`. Add `-NoBrowser` to a normal launch to start services without opening a browser. The launcher can install missing project dependencies, so a first launch needs internet access. Supabase account creation and sign-in still require your own account; the launcher does not create identities or bypass authentication.

The manual commands below are also available.

Use Node.js 20.9 or newer and Python 3.11 or newer. The project was checked with Node 24 and Python 3.13. Run commands from this folder unless a command changes directories.

In one PowerShell terminal, start the API:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m classguard.cli init-db
.\.venv\Scripts\python.exe -m uvicorn classguard.main:app --host 127.0.0.1 --port 8000 --reload --no-proxy-headers
```

In another terminal, start the web app:

```powershell
cd apps/web
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open **http://localhost:3000**. API documentation is at **http://localhost:8000/docs**. Use localhost for the web URL to match the API's default allowed origin. Only copy example environment files when setting up a new checkout so existing configuration is preserved.

The development UI opens without provider credentials. Its setup screen and local design preview are available. Protected API operations return a clear configuration error until Supabase is configured.

## Enable institution onboarding and class planning

1. Configure a Supabase project with asymmetric JWT signing and confirmed email accounts. Keep email confirmation enabled, or use a trusted institutional identity flow. Each protected API request verifies the JWT and then retrieves current account details from Supabase.
2. Set the API `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` in `apps/api/.env`. The key must be a public `sb_publishable_` key. This is now required even if an older setup used only the project URL.
3. Set `NEXT_PUBLIC_SUPABASE_URL` and the public publishable key in `apps/web/.env.local`.
4. Run `python -m classguard.cli init-db` in the API environment. This also adds the new onboarding tables to an existing foundation database without replacing its records.
5. Restart both applications and sign in. Create an institution in the app, or select an existing membership.
6. As an administrator, open **People**, invite a teacher or student, and copy the generated link. Share it yourself with the intended recipient. No email is sent by ClassGuard.
7. The recipient opens the link and signs in with the invited account to accept. Supabase account creation and password recovery remain provider-managed in this build.
8. Administrators and teachers can create scheduled classes. Open a class to manage student enrollment. Students see only their enrolled classes.

Keep service-role keys and media-provider secrets out of browser configuration. Invitation secrets are returned once and stored as hashes on the server. Links use a browser fragment so the secret is not sent in the page URL to the web server. A matching authenticated account is still required to accept. Invitations cannot grant administrator access or change an existing membership. Trusted local CLI provisioning remains available; see `apps/api/README.md`.

## Checks

```powershell
# From apps/api with its virtual environment installed
.\.venv\Scripts\python.exe -m pytest -q

# From apps/web
npm run typecheck
npm run build
```

See `docs/VALIDATION.md` for the checks performed on this delivery and their limits.

The security update adds bounded requests, local per-account/IP rate limits, current confirmed-email checks, conservative invitation email matching and browser framing protection. These are development safeguards, not a production security certification. See `docs/SECURITY_REVIEW.md` before deploying or collecting student data.

## Next implementation milestone

Introduce the reusable classroom/session model, then integrate LiveKit behind server-enforced admission. The release plan requires a real two-device call, effective remove/rejoin controls, signed media events and reconciled attendance before a pilot. Onboarding must also be exercised with a real configured Supabase project before institutional use.

Production requires configured Supabase, PostgreSQL, LiveKit, HTTPS, schema migrations, operations/backup setup and institution policy decisions. The scaffold has no production cloud deployment or paid-service configuration.

The configured development workspace now uses Supabase PostgreSQL. Fresh checkouts still default to SQLite until their ignored environment files are configured. The cloud schema is recorded in `infra/sql/classguard_cloud_schema.sql`; application passwords, database credentials, local records and generated first-login files are excluded from Git.
