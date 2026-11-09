# Delivery validation

## Cloud connection and startup automation — 9 November 2026

All **120 API tests passed**, including PostgreSQL schema-routing and unchanged SQLite foreign-key checks. The Windows launcher passed syntax/readiness checks, reused healthy project services without changing their PIDs or rebuilding an unchanged frontend, and subsequently cold-started both applications. All four frontend security-header probes passed against the running build.

The real Supabase PostgreSQL session-pooler connection passed certificate and hostname verification. The runtime role accessed all six private application tables, completed related ORM writes and reads inside a rolled-back transaction, and was denied access to Auth user records and schema creation. Supabase's security advisor returned no findings after the schema was applied. See `CLOUD_SETUP.md` for the access model and limits.

The administrator's real password-login attempt remained blocked by the provider's **Email not confirmed** response. This is not a completed sign-in or institution-creation acceptance test. Public hosting and live video remain unimplemented.

Before repository upload, a limited scan checked 77 project files and 105 historical Git blobs for the actual configured credentials; no matches were found. Private environment files, database files, runtime logs and first-login records remain ignored. This is not an exhaustive secret-detection guarantee.

## Security review — 6 November 2026

All **104 API tests passed**: the original 50 plus 54 adversarial and hardening cases. Coverage includes foreign tenant IDs, mixed-role membership, mass assignment, copied/Unicode-confusable invitations, SQL metacharacters, malformed JWT headers and temporal claims, provider account rejection/outage, stale JWT email, bounded request bodies (including chunked/false-length bodies), spoofed forwarding headers, account quotas and validation redaction. Tests use disposable SQLite databases and controlled identity-provider responses.

TypeScript and the production build passed. Four actual HTTP frontend responses passed `node scripts/check-security-headers.mjs`. A separate local-origin iframe was refused by the browser, and ordinary direct navigation still worked. Actual API HTTP probes returned `413` for an oversized JSON body, rejected an untrusted-origin CORS preflight with `400` and no allow-origin header, and returned `503` when authentication was unconfigured.

`npm audit` reported zero known vulnerabilities across its 88-package dependency inventory. `pip-audit` checked the 33 resolved Python application/test packages with zero findings and zero skipped packages. A limited working-tree signature scan found no matching secret patterns in 68 source/document files. These scans do not prove absence of unknown vulnerabilities or all possible secrets. Full findings and open gaps are in `SECURITY_REVIEW.md`.

No live Supabase, PostgreSQL, public hosting, real student accounts, or LiveKit deployment was attacked or validated. Current-account checks use a new required backend public key setting; deployed behavior, logout/revocation and email confirmation need acceptance on the actual provider project.

## Onboarding build — 6 November 2026

The onboarding API suite passed **50 tests**, including all 25 original identity, tenant and attendance cases. Added coverage checks institution bootstrap, directory permissions, email-bound invitations, hash-only secret storage, expiry and revocation, role escalation denial, protected administrator memberships, class ownership, enrollment removal and student timetable visibility.

Concurrent invitation acceptance is covered by the suite and an independent eight-request SQLite probe: exactly one request succeeded, seven were rejected, and one membership was stored. A deterministic accept/revoke interleaving test verifies that revocation reports a conflict if acceptance wins. An independent eight-request first-login probe also stored exactly one directory identity without request failures.

An independent additive-upgrade check created the four original tables with existing class, membership and enrollment records, then ran table initialization twice. The two new tables were added, original columns and records were preserved, and repeat initialization succeeded. PostgreSQL DDL compiled for all six tables; this was not a live PostgreSQL execution test.

Live local API checks confirmed healthy startup, the onboarding capability flags and CORS preflight support for member updates. The local development database was upgraded using the normal `init-db` command. Provider credentials remain unconfigured: successful real Supabase authentication and the full multi-account browser workflow have not been established by these checks.

The TypeScript check and Next.js production build passed, including the new `/people` and `/join` routes. Browser checks against that production build verified the People onboarding screen, missing-invitation guidance, a test fragment surviving the sign-in dialog, disabled unconfigured sign-in fields, Escape dismissal, setup feature flags, and preview-mode restrictions. The People and invitation layouts were inspected at 390px and 1,200px CSS viewport widths with no horizontal page overflow. No browser console errors were reported during these flows. The temporary viewport override was reset afterward.

These browser checks exercised unconfigured and local-preview states. The authenticated administrator, teacher and student operations were tested through the API authorization suite and reviewed in the frontend source; they still need end-to-end browser acceptance against a real Supabase project.

## Foundation delivery — 4 November 2026

Checked 4 November 2026. This evidence applies to the initial development foundation.

| Check | Result |
| --- | --- |
| Clean Python virtual environment, installed from `requirements-dev.txt` | Passed on Windows with Python 3.13, without inheriting system packages |
| API/identity/tenant/attendance tests | 25 passed |
| TypeScript check | Passed |
| Next.js production build | Passed after final accessibility correction; all dashboard, classes, attendance, setup and manifest routes generated |
| HTTP smoke checks | Frontend returned 200; API `/health` reported `ok`; `/v1/capabilities` accurately reported the foundation feature set |
| Unconfigured authentication | `/v1/me` returned 503 with a configuration message |
| Browser navigation | Dashboard, Classes, Setup and Attendance views opened successfully |
| Local design preview | Explicit sample labels, class search and details dialog worked |
| Modal keyboard behavior | Escape dismissed the class dialog; focus began on its close control |
| Sign-in state | Unconfigured form showed setup guidance and disabled submission |
| Connection refresh | API status remained online after refresh |
| Responsive layout | Inspected desktop and phone layouts; measured 1,200px and 390px CSS viewports without horizontal page overflow |
| Browser errors | No console errors reported during checked flows |
| Mobile accessible name | Header sign-in button retained an explicit label when its visible text was hidden |
| PRD v1.1 | 20 pages rendered and visually reviewed; source-content check preserved 514 authored blocks/cells; 16 clickable reference links |

The API suite covers institution access denial, student enrollment filtering, role restrictions, revoked membership, signed JWT validation, forged identities, timezone normalization, overlapping connections, reconnect gaps, breaks, missing exits, zero teaching duration and daylight-saving transitions.

The clean test run emitted one upstream Starlette warning about its legacy httpx test-client compatibility. Tests passed. Revisit the test-client dependency before the next framework upgrade.

## Verification limits and next gates

Supabase login against a real configured project and PostgreSQL runtime behavior have not been exercised. PostgreSQL DDL compilation was checked for the four foundation tables and subsequently the six onboarding tables. Browser layout checks do not replace real Android/iOS device testing.

LiveKit calls, waiting-room admission, media controls, provider events, synchronized polls, attendance collection, production tenant operations and AI features remain future milestones. The implemented attendance library requires authoritative intervals from the future event pipeline. Production security, accessibility conformance, load capacity, backups and real-provider institution onboarding require separate acceptance before a pilot.

Local preview servers are temporary verification processes. Restart them using the root README when continuing development.
