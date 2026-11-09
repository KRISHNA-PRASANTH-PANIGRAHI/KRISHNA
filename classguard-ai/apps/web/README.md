# ClassGuard AI web

Next.js, React and TypeScript frontend for ClassGuard's v0.2 institution setup and class planning milestone.

## Local setup

Run from this directory with Node.js 20.9 or newer.

```powershell
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open http://localhost:3000. Keep existing environment files when resuming an already configured checkout.

`NEXT_PUBLIC_API_URL` points to FastAPI, defaulting to http://localhost:8000. Set the Supabase URL and public publishable key to enable sign-in. The API must use the same Supabase project. Accounts are created through Supabase's provider management; the app does not create identities or send email. See `../api/README.md` for backend configuration and optional trusted CLI provisioning.

## Current behavior

Dashboard, class search/details, setup status, sign-in, People, and invitation acceptance screens are implemented. After signing in, create an institution from Setup or the initial dashboard; its creator becomes an administrator. Administrators can generate teacher/student invitation links, copy them for manual sharing, revoke pending invitations, change teacher/student roles, and remove or restore access. Administrator memberships cannot be changed through these controls.

Invitations use `/join#token=…`: the fragment stays in the browser and survives the sign-in modal, and is sent only in the authenticated acceptance request body. After success, the fragment is removed from the address bar. Links expire in 7 days, are bound to the invited email, and can be used once. Raw links are shown only immediately after creation and are cleared when the account or institution changes. A new link replaces the prior pending invitation to the same email; no email is sent automatically.

Configured administrators and teachers can create persisted class plans through the API. Open a class's details to enroll or remove active student members. Teachers can manage only their own classes. Students see their enrolled plans. Changing a member's teacher/student role clears their existing student enrollments; removing access preserves enrollments for restoration. Institution and identity permissions are enforced on the API, including when the frontend state is stale.

The design preview displays clearly labeled sample classes in memory and cannot perform institution mutations. Attendance reporting and live meetings are marked as planned until their services are integrated.

The app has a web manifest and SVG icon. Service-worker caching, push notifications and device-specific install behavior remain later validation work. Live classes always require a connection.

## Checks

```powershell
npm run typecheck
npm run build
```

After starting the production build with `npm run start`, run `node scripts/check-security-headers.mjs`. This checks the actual page, static-file and not-found responses for framing, MIME, referrer and browser-permission protections. The web app sends `frame-ancestors 'none'` and `X-Frame-Options: DENY` to prevent embedding. Its current CSP restricts framing, base URLs, objects and form targets; it does not yet restrict script sources or provide nonce-based XSS containment. [Next.js header configuration](https://nextjs.org/docs/app/api-reference/config/next-config-js/headers), [MDN frame-ancestors](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors).

Supabase sessions persist in browser storage so page reloads retain sign-in. On a shared device, sign out before leaving. Browser storage is accessible to scripts running in this origin; a future XSS flaw would threaten these tokens. No unsafe HTML rendering sink was found in the current application source, but this review is not proof that every dependency or browser flow is XSS-free. Production must use HTTPS; configure and verify HSTS at the public HTTPS endpoint rather than the local HTTP development server.

The development server binds to loopback. Invitation links use the current website origin. A localhost link works only on the same machine; for physical-device testing and sharing links across devices, open the app through a deliberate shared HTTPS environment and configure the API's allowed origins before generating invitations.
