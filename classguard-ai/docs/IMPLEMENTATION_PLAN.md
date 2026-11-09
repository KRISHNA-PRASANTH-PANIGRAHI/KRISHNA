# ClassGuard AI implementation plan

Updated 6 November 2026. Scope follows the supplied PRD v1.0. Institution onboarding and enrollment now extend the development foundation. The following milestones distinguish local code readiness from a usable institutional service.

The onboarding build implements institution creation, teacher/student invitation links, non-administrator membership management and class enrollment. Account creation remains in Supabase. These flows still require acceptance with real configured accounts; a passing local authorization suite does not establish that provider integration or production operations have been validated. The next implementation work is the classroom/session split and authenticated media admission in MVP 0.2.

## Milestones and release evidence

| Milestone | Deliverables | Evidence required |
| --- | --- | --- |
| Foundation | Responsive shell, sign-in integration, health/capabilities API, membership checks, persisted classes, attendance calculation module | Frontend typecheck/build, API unit and authorization tests, clear unconfigured states |
| MVP 0.1 | Institution bootstrap, invitations, role management, enrollment and class scheduling | Admin provisions institution, teacher creates class, enrolled student sees the right timetable through normal UI |
| MVP 0.2 | LiveKit prejoin, authenticated waiting room, admission, device controls, chat, hand raise, lock/remove/end | Real teacher and student complete a two-device session and removal survives reconnect |
| MVP 0.3 | Verified event ingestion, attendance intervals, correction history, exports | Duplicate/reordered events converge, network gaps are reviewed, report reconciles to evidence |
| MVP 0.4 | Poll delivery, quiz responses, eligible-response counts and teacher dashboard | Retry-safe submissions and correct denominators after reconnect |
| Pilot | PostgreSQL migrations, device matrix, accessibility, restore drill, limits, support process | Institutional acceptance, measured load test, privacy/retention decisions and documented incident ownership |
| Later | Reviewed AI study materials, assignments, parent views, breakout rooms, recording | Each module passes its own usability, privacy, accuracy and permission gates |

## Attendance rules

Measure the union of server-confirmed connection intervals, clipped to the actual teaching window. Exclude explicit class breaks from both connected time and teaching duration. Waiting-room time is separate. Overlapping devices cannot increase attendance above 100%.

`connected attendance = counted connected seconds / counted teaching seconds × 100`

A zero-length counted teaching window returns no percentage. Missing departure evidence makes the result provisional. An optional reconnect grace period changes the live status display only. It does not silently credit disconnected minutes. Teachers may add a reasoned correction while preserving the measured result and event history.

| Test scenario | Expected result |
| --- | --- |
| 10:00-10:30 and 10:40-11:00 in a one-hour session | 3,000 seconds and 83.33% |
| Two devices with intervals 10:00-10:40 and 10:20-11:00 | 3,600 seconds and 100% |
| Five minutes in waiting room, then 55 minutes connected | 55 counted minutes |
| Teacher ends at 10:45 | Actual 45-minute denominator |
| Ten-minute explicit break during a 60-minute session | 50-minute denominator, break removed from connection time |
| Missing end event | Provisional/needs-review result, reconciled before finalization |

## Participation rules

Keep attendance, participation, quiz accuracy and connectivity separate. An eligible activity is one that targeted the student and was delivered with enough response time. Proposed response-time policies require institution validation and accommodations.

`participation = submitted eligible activities / eligible activities`

Display counts next to percentages. A wrong quiz answer still counts as participation. Distinguish answered, delivered-but-unanswered, not-delivered, excused and late. Zero eligible activities means insufficient activity data. Deduplicate submission IDs and enforce the deadline on the server.

When institutions enable page-visibility collection, disclose the exact signal and its purpose. A hidden tab may reflect opening lesson materials, accessibility software or mobile background behavior. Store only the classroom's visibility state. Avoid inferring the identity or content of another application. [Page Visibility API](https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API)

## Admission lifecycle

Use requested, waiting, approved, connected, disconnected, rejected, removed and expired states. Approval is bound to a user and class session. A copied invitation identifies a class but does not authorize entry. Every token issue rechecks enrollment and active session policy. Ending a class invalidates pending approvals. Re-admitting a removed participant requires a deliberate teacher action.

Teacher actions that restore publishing permission must still let the student choose when to enable a microphone or camera. Define host recovery, substitute teachers and device transfer before the pilot.

## Cross-tenant acceptance cases

- A user in institution A cannot read, mutate, export or subscribe to institution B's data by changing an identifier.
- A student cannot create classes or grant themselves teacher privileges through the UI, request body or token metadata.
- A teacher cannot mutate a colleague's class without an explicit assignment.
- Revoked membership affects new requests and eventually active media/application privileges.
- Object storage, caches and asynchronous work use the same verified scope as API requests.
- Support access is time-limited, authorized and audited when introduced.

## Device and accessibility gates

Test actual Safari on iPhone/iPad, Chrome on Android and supported desktop browsers. Width emulation verifies layout only. A real-device meeting test must cover microphone denial, camera switching, incoming screen share, rotation, audio-only participation, reconnect, screen lock and foreground recovery.

Feature-detect screen capture and offer a clear unavailable state when unsupported. PWA installation is optional. Avoid caching protected API responses, tokens or meeting media. Offline views must show that live classes and server submissions need connectivity. Use server timestamps after resume rather than relying on timer callback frequency.

## Decisions still needed for a pilot

Pilot institution and class size, attendance threshold, late-entry rule, correction ownership, LiveKit hosting model, region, retention, minor/guardian workflows, identity-provider policy, expected budget and support owner. These remain open decisions rather than invented requirements.
