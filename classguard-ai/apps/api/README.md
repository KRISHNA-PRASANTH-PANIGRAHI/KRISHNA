# ClassGuard AI API

Version 0.2 implements institution creation, manual invitation links, membership administration, student enrollment, tenant-scoped class planning, and a tested connected-time calculation library. Live classrooms, admission, provider webhooks, attendance reports, and polls are subsequent milestones. `/v1/capabilities` reports those boundaries to the web app.

## Run locally

Use Python 3.11 or newer. Run the following from `apps/api`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m classguard.cli init-db
.\.venv\Scripts\python.exe -m uvicorn classguard.main:app --reload --host 127.0.0.1 --port 8000 --no-proxy-headers
```

The health endpoint works before identity is configured. Protected endpoints return `503` until both `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` are set. Use the public `sb_publishable_` key; secret and legacy service-role keys are rejected. Supabase must use ES256 or RS256 signing. Tokens are checked against the project's JWKS, issuer, audience, expiration and UUID subject. Unsupported or oversized tokens are rejected before key lookup, and JWKS network failures have a short retry backoff.

Each protected request then retrieves `/auth/v1/user` from the configured Supabase origin, with a five-second timeout and a bounded response. The returned ID must match the signed subject, the account must be non-anonymous, and a current email with a confirmation timestamp must exist. Invitation matching uses this current email instead of the potentially stale JWT email. Redirects are not followed with credentials. Provider errors deny access; there is no offline fallback. Keep Supabase's email-confirmation policy enabled or use a trusted institutional provider: a provider configured to auto-confirm arbitrary addresses cannot establish mailbox ownership. Real provider behavior still needs integration testing.

Set `CORS_ORIGINS` to a JSON array of exact frontend origins. Set `DATABASE_URL` to `postgresql+psycopg://...` when using PostgreSQL. The database must be private to the API, with least-privilege credentials. If exposing tables through Supabase's Data API later, add and verify PostgreSQL RLS first. Current authorization is enforced through the API and database foreign keys.

`init-db` creates missing tables for development. Run it again after updating from 0.1: it adds `account_identities` and `invitations` while preserving existing institutions, memberships, classes, and enrollments. It does not alter or migrate existing tables. Adopt versioned Alembic migrations before changing deployed schemas.

## Institution setup in the app

1. Configure Supabase in both applications and provision identity-provider accounts with confirmed email addresses. Keep Supabase email confirmation enabled. This release signs in existing accounts; it does not send invitation emails or create Supabase users.
2. Sign in and create an institution from the People view. The API assigns the creator an administrator membership in the new institution only. Creation does not verify institutional ownership or an email domain.
3. An administrator creates an invitation for a teacher or student and manually shares the generated link. The recipient signs in with the invited email address, then accepts it.
4. Administrators can change teacher/student roles, deactivate or reactivate these memberships, and revoke unused invitations. Existing administrator memberships cannot be changed through this API.
5. Administrators and teachers enroll active student members into classes. Teachers can manage only classes they created. Enrolled students then see the class in their timetable.

Invitations expire after seven days. The raw secret is returned only when the invitation is created; the database stores a SHA-256 hash. Reissuing for the same institution and normalized email revokes the old outstanding link. Acceptance checks the current provider-verified email, consumes the invitation atomically, and creates its membership in the same transaction. ASCII letters are compared without case; distinct non-ASCII characters are preserved. It rejects any existing membership instead of changing a role or restoring revoked access. Administrator status cannot be granted by an invitation. Revoke and reissue outstanding invitations created by a previous version that used Unicode casefolding; the original spelling cannot be reconstructed from a lossy normalized record.

The account directory learns email addresses from authenticated requests and accepted invitations. Legacy CLI-provisioned members display a user UUID until they sign in. Directory email is descriptive; roles always come from institution membership records. Changing a teacher/student role removes that member's student enrollments, so switching roles back cannot restore obsolete access. Deactivation alone preserves enrollments for a deliberate administrator reactivation, while immediately denying new protected API requests.

## Provision an institution

The CLI remains available for trusted local administration. First create or invite the account in your own Supabase project, and obtain its user UUID. This command does not create an identity or send an invitation.

```powershell
python -m classguard.cli provision --institution-name "Example College" --user-id "SUPABASE_USER_UUID" --role admin
python -m classguard.cli provision --institution-id "INSTITUTION_UUID" --user-id "TEACHER_UUID" --role teacher
python -m classguard.cli provision --institution-id "INSTITUTION_UUID" --user-id "STUDENT_UUID" --role student
python -m classguard.cli enroll --institution-id "INSTITUTION_UUID" --class-id "CLASS_UUID" --user-id "STUDENT_UUID"
```

The first command prints the generated institution UUID. Provisioning an existing membership explicitly updates its role and reactivates it. Only trusted operators should run this command. A student must have an active membership before enrollment.

## API contract

Interactive API documentation is at `http://localhost:8000/docs` while the server runs.

| Method and route | Behavior |
| --- | --- |
| `GET /health` | Liveness only. Returns `{ "status": "ok", "service": "classguard-api" }`. |
| `GET /v1/capabilities` | Public integration configuration and implemented feature flags. |
| `GET /v1/me` | Verified identity plus active institution memberships. |
| `POST /v1/institutions` | Authenticated account creates an institution with `{ "name": "Example College" }`; receives an administrator membership. |
| `GET /v1/institutions/{uuid}/members` | Admin sees all members; teacher sees active students; student denied. |
| `PATCH /v1/institutions/{uuid}/members/{user_uuid}` | Admin updates teacher/student `role` and/or boolean `active`; administrator targets and grants denied. |
| `GET /v1/institutions/{uuid}/invitations` | Admin sees invitation email, role, dates and status; no secret or hash is returned. |
| `POST /v1/institutions/{uuid}/invitations` | Admin supplies `email` and teacher/student `role`; receives one-use `token` plus invitation details. |
| `POST /v1/institutions/{uuid}/invitations/{invite_uuid}/revoke` | Admin revokes an unused invitation. Accepted invitations return `409`. |
| `POST /v1/invitations/accept` | Authenticated recipient supplies `{ "token": "..." }`; receives the new membership. |
| `GET /v1/institutions/{uuid}/classes` | Admin sees institution classes. Teachers see classes they created. Students see enrolled classes. |
| `POST /v1/institutions/{uuid}/classes` | Admin or teacher creates a class plan. Student requests are denied. |
| `GET /v1/institutions/{uuid}/classes/{class_uuid}/enrollments` | Admin or class-owning teacher sees its enrolled members. |
| `POST /v1/institutions/{uuid}/classes/{class_uuid}/enrollments` | Admin or class-owning teacher enrolls `{ "user_id": "..." }`; repeated enrollment is idempotent. |
| `DELETE /v1/institutions/{uuid}/classes/{class_uuid}/enrollments/{user_uuid}` | Admin or class-owning teacher removes enrollment; repeated removal returns `204`. |

All protected requests use `Authorization: Bearer <Supabase access token>`. Membership and role come from the database on every request. Clients cannot forge creator identities or grant themselves access to an existing institution. Unknown, inactive, or unauthorized institutions return `404`. Within an accessible institution, disallowed roles return `403`. All request schemas reject unexpected fields.

Member list responses use `{ "items": [{ "user_id": "...", "email": null, "role": "student", "active": true }] }`. Invitation list responses use `{ "items": [{ "id": "...", "email": "student@example.edu", "role": "student", "created_at": "...", "expires_at": "...", "status": "pending" }] }`; status is one of `pending`, `accepted`, `revoked`, or `expired`. Invalid invitation secrets return `404`, wrong-account acceptance `403`, unavailable invitations `410`, and existing membership conflicts `409`. Invitation tokens should be placed in the client URL fragment and sent to acceptance only in a POST body, never query parameters or logs.

`GET /v1/me` returns the following shape.

```json
{
  "id": "user-uuid",
  "email": "user@example.edu",
  "memberships": [
    { "institution_id": "institution-uuid", "institution_name": "Example College", "role": "teacher" }
  ]
}
```

Class creation accepts the following fields. The timestamp must contain an explicit timezone. Titles and subjects are trimmed and required, duration is an integer from 5 to 480 minutes, and description is optional.

```json
{
  "title": "Calculus revision",
  "subject": "Mathematics",
  "description": "Limits and derivatives",
  "starts_at": "2026-11-10T10:00:00+05:30",
  "duration_minutes": 50
}
```

The response adds `id`, `institution_id`, `created_by`, and `created_at`. Timestamps are normalized to UTC. List responses wrap the array as `{ "items": [...] }`. The initial class plan represents one scheduled occurrence. Recurring classroom definitions and separate session lifecycle records will be introduced with the live-class milestone.

## Attendance calculation

`classguard.attendance.calculate_attendance` accepts server-confirmed connection intervals and explicitly excluded break intervals. It normalizes timestamps to UTC, merges overlaps across devices, clamps connections to the teaching window, and subtracts merged breaks from both the connected duration and denominator. Reconnect gaps receive no automatic credit. Open or unconfirmed connections require review and contribute no inferred duration. A zero teaching window returns a null percentage and requires review.

This is a calculation library, not an attendance API. A future verified webhook/event pipeline must deduplicate provider events, reconcile ordering and missing exits, retain provenance, and then supply intervals. Waiting-room time must be excluded by that pipeline. The result does not grade students or estimate their attention.

## Verification

```powershell
python -m pytest
```

Tests cover tenant denial, invitation expiry and revocation, hash-only secrets, wrong-email rejection, concurrent one-use redemption, revocation race feedback, membership escalation prevention, class ownership, enrollment removal, role-switch cleanup, timestamp normalization, invalid JWT claims/signatures, overlapping devices, reconnect gaps, excluded breaks, missing exits, and daylight-saving transitions. The test-only authentication dependency override is never part of the server configuration.

## Integration gates

Current local safeguards cap API bodies at 64 KiB, aggregate headers at 32 KiB, and body receipt at ten seconds. Compressed bodies are rejected. Fixed windows allow 240 requests/minute per ASGI peer, 120 protected requests/minute per verified account, 30 writes/minute per account, and five institution creations/hour per account. Limits are per process, reset on restart and use a bounded in-memory store. They are not distributed DDoS protection or durable institution quotas. They return `429` with `Retry-After`; oversized bodies return `413`. Validation errors omit raw submitted values.

Run local Uvicorn with `--no-proxy-headers`. In a deployed proxy environment, explicitly trust only the actual proxy addresses and ensure that proxy overwrites forwarding headers. Put shared rate limits, connection/body limits and HTTPS at the public edge. Test legitimate classroom traffic behind a shared school network when tuning these values.

Before a real pilot, implement versioned database migrations, pagination, durable quotas and shared edge rate limits, idempotency keys for creation writes, admission and lock state, media-token issuance after authorization, verified provider events, audit logs, and backup/restore checks. Validate concurrency against a real PostgreSQL instance; local tests use SQLite. Account registration/recovery and delivery of emails remain provider/operator responsibilities. Keep admission and LiveKit tokens fail-closed until their state transitions and removed-participant re-entry tests are implemented. The security findings and remaining session-policy limits are in `../../docs/SECURITY_REVIEW.md`.

Official integration references are [Supabase JWT verification](https://supabase.com/docs/guides/auth/jwts), [PyJWT usage](https://pyjwt.readthedocs.io/en/stable/usage.html), and [LiveKit access tokens](https://docs.livekit.io/frontends/reference/tokens-grants/).
