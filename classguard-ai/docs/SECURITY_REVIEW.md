# ClassGuard AI local security review

Reviewed 6 November 2026. Baseline commit: `390239b`. Scope: this local development application, its source, resolved dependencies, loopback HTTP services and disposable test databases. No external institution, real provider account or production system was targeted. This is an exploit-oriented development review, not a certification or a complete penetration test.

## Assessment

The baseline had meaningful gaps and should not be described as production-secure. The confirmed local findings below are corrected or mitigated in this update. The tested tenant, role, invitation and SQL-injection attacks did not bypass the patched checks. Production acceptance remains necessary, especially for identity-provider policy, distributed abuse controls, auditing and database deployment.

## Findings and fixes

Severity here is a contextual engineering judgment for a future internet-facing application; no CVSS score or observed production compromise is claimed.

| Finding | Evidence and preconditions | Change and residual limit |
| --- | --- | --- |
| **Medium: unbounded request bodies** | A disposable authenticated request containing valid JSON plus whitespace totaling 2,097,195 bytes returned `201`. Field-length validation did not limit the wire body. This demonstrated missing limits, not a measured server crash. | Bodies now have a 64 KiB cap before parsing, including chunked and false-length requests. Actual loopback HTTP returned `413` after the fix. Header and body-receipt limits were also added. Public edge connection and bandwidth limits remain necessary. |
| **Medium: unrestricted creation/request bursts** | A disposable baseline probe sent 40 institution-creation requests and all returned `201`. The baseline had no API throttling. | Local peer/account/write limits and an account institution-creation limit were added. A test using real JWT verification with a controlled provider accepted five creations and rejected the next three with `429`, even while forwarding headers changed. Limits are per process and reset on restart: shared limits and durable quotas remain open. |
| **Medium, conditional: invitation email collision** | Unicode casefolding equated `straße@school.test` and `strasse@school.test`, and similarly the Kelvin sign and ASCII K. A copied invitation could therefore match a distinct signed mailbox string. Exploitation requires the secret and a provider that accepts those distinct identities; no live Supabase exploit was claimed. | ASCII case-insensitivity is retained while non-ASCII codepoints stay distinct. Regression requests now return `403` for the different mailbox and permit the correct account. Revoke/reissue outstanding invitations created with old lossy normalization before real use. |
| **Medium: stale/unchecked account email** | The original API relied solely on signed JWT email and a deployment instruction to confirm accounts. JWT verification alone cannot establish current account/email state. | After local signature checks, the API now retrieves the current Supabase user, matches its ID and requires a non-anonymous account with a confirmed email. Stale JWT email is replaced with the current address; provider failures deny access. Tests mock this provider boundary. Real provider behavior and confirmation policy still need verification. |
| **Medium: frameable application pages** | Baseline page responses had neither `frame-ancestors` nor `X-Frame-Options`. A hostile page could embed the future authenticated UI; no real user was tricked into an action. | Pages now send `frame-ancestors 'none'` and `X-Frame-Options: DENY`. A separate local-origin iframe was refused after the fix, while direct navigation worked. MIME, referrer and device-permission headers were added. The CSP is not a script allowlist. |
| **Low/availability: avoidable identity-provider work** | Unsupported/malformed JWT headers reached key lookup before rejection. Failed key fetches could retry immediately. | Algorithm/key-ID/critical-header/size checks precede JWKS lookup. Provider network failures back off for five seconds; the installed JWT library already has unknown-key refresh cooldown. Tests verify zero key lookups for rejected headers and one fetch for eight immediate outage retries. |

Additional hardening converts nonfinite signed time claims into `401` rather than an unhandled error, prevents credential-following provider redirects, bounds provider responses, and omits raw values from API validation errors. These are robustness improvements; no unauthenticated ability to forge a correctly signed nonfinite token is claimed.

## Attacks that were blocked in the tested cases

- Using institution B's class ID through an administrator's institution A route: denied without changing B's enrollment.
- Being an administrator in A and a student in B, then trying to borrow the administrator role in B: denied.
- Supplying role, institution, user, expiry or acceptance fields to change invitation authority: rejected.
- Reusing, revoking, expiring or racing a single-use invitation: existing and new regression tests preserved one-use behavior.
- Forging signatures, changing issuer/audience, using unsigned/HMAC tokens or unsupported critical headers: rejected.
- Sending SQL metacharacters in a class title: stored as literal data, with membership records intact.
- Probing common frontend secret/source/database paths: returned `404`. No unsafe application HTML-rendering sink or open redirect was found in the reviewed source; this is not exhaustive XSS proof.

## Verification and reproduction

Run from the indicated application directory with its dependencies installed:

```powershell
# apps/api
python -m pytest -q

# apps/web
npm run typecheck
npm run build
npm run start
# In a separate terminal while that local server runs:
node scripts/check-security-headers.mjs
npm audit
```

All **104 API tests passed**: 50 existing tests plus 15 authorization, 32 identity and seven request-limit security cases. TypeScript and production build checks passed. The header script passed for People, Join, the icon and a 404 response. One existing Starlette/httpx test-client deprecation warning remains.

The dependency audit found **zero known advisories** in npm's 88-package inventory and all 33 resolved Python application/test packages. Python auditing used the exact installed version list with `pip-audit --no-deps --disable-pip`; zero packages were skipped. No application dependency was changed. A limited signature scan found no matching secrets in 68 working-tree source/document files; it did not scan every historical commit or every possible credential format. Scanner output and disposable probes are retained under the workspace's `work/security` directory.

Dependency tools report known advisories, not whether the application is safe against unknown flaws or malicious logic. [PyPA pip-audit documentation](https://github.com/pypa/pip-audit)

## Gaps still open before student use

1. **Real provider and session acceptance.** Configure the same public `sb_publishable_` key in the backend, keep email confirmation enabled or use trusted institutional SSO, and test account deletion, changed email, password reset, logout and ban behavior. Fresh account lookup fails closed on provider rejection, but immediate revocation of every unexpired access token is not established. Supabase documents that access JWTs can remain valid until expiry; use a verified session-denial design if immediate revocation is required. [Supabase sign-out semantics](https://supabase.com/docs/guides/auth/signout), [current-user retrieval](https://supabase.com/docs/reference/javascript/auth-getuser)
2. **Shared abuse controls and bounded data growth.** Add public-edge limits, durable per-institution quotas, pagination and sensible creation policies. Current counters reset and are not shared by workers. A new workspace name does not verify that its creator represents that institution.
3. **Audit history and administrator protection.** Record who invited, changed roles, removed access and altered enrollment, with appropriate retention and access controls. Administrator MFA/step-up authentication and recovery/ownership transfer are not implemented.
4. **Production database and transport.** Validate tenant isolation and races on PostgreSQL, add versioned migrations, private database credentials, TLS/HSTS, backups and a restore test. Supabase Data API exposure must be reviewed separately; API filters do not establish database RLS. Local tests used SQLite and loopback HTTP.
5. **Browser session protection.** Sessions persist in browser storage. A future same-origin XSS flaw could expose them, and shared school devices need a deliberate session policy. Add and test a nonce-based script CSP and evaluate a server-session/HttpOnly-cookie design with its required CSRF controls. The present framing CSP does not solve XSS.
6. **Unbuilt meeting features.** LiveKit admission, camera/microphone permissions, participant removal/re-entry, media tokens, recordings, signed webhook ingestion and attendance integrity are not yet implemented, so their security cannot be assessed from this build.

The input, authentication, CORS and request-limiting checks follow the concerns described by [OWASP's REST security guidance](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html). A public pilot should be reviewed again against its actual hosting, provider policy and completed meeting workflows.
