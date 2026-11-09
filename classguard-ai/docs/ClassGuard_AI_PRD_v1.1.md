# CLASSGUARD AI

## Product Requirements Document

**Version 1.1 | 04 November 2026 | Draft for validation**

Beyond Attendance. Towards Accountability.

A responsive virtual classroom platform for schools, colleges, universities and coaching institutes. ClassGuard brings verified access, reliable session records, teacher controls and observable participation into one learning environment.

**Product direction**
Web application first, with a Progressive Web App foundation and a shared backend for future mobile clients.

**This release of the document**
An engineering refinement of the user-supplied PRD v1.0. It adds measurable rules, authorization boundaries, failure handling and milestone evidence. Requirements describe intended behavior. Implementation status is recorded separately in the project README and validation report.

**Project folder**
online classes

<!-- page -->
# 01  Document control and navigation

| Item | Definition |
| --- | --- |
| Product | ClassGuard AI |
| Version and date | 1.1, 04 November 2026 |
| Status | Draft for validation before institutional pilot |
| Baseline | User-supplied ClassGuard_AI_PRD_v1.0.pdf, dated 03 November 2026 |
| Primary client | Responsive web application for desktop, tablet and phone |
| Primary roles for MVP | Student, teacher, institution administrator |
| Product owner | To be assigned by the project owner |

## Changes from v1.0

- Defined attendance interval union, actual teaching windows, breaks, missing evidence and timezone handling.
- Defined participation denominators and separated response submission from answer correctness.
- Added admission states, removal/rejoin tests, tenant boundaries and API/event design.
- Distinguished the development foundation, usable MVP, institutional pilot and production release.
- Corrected reference formatting and added repository/license observations and primary sources.

## Reading map

| Pages | Subject |
| --- | --- |
| 3-5 | Product scope, roles and user journeys |
| 6-10 | Identity, classrooms, attendance, participation and learning tools |
| 11-14 | Cross-device experience, architecture, data and API design |
| 15-17 | Privacy, quality targets and open-source references |
| 18-20 | Delivery gates, open decisions and sources |

**Priority key** - P0 is required before the first institutional pilot. P1 follows the core pilot workflow. P2 requires a separate evaluation or product decision. Foundation code implements only a subset of P0. Proposed thresholds are planning assumptions until validated with the institution.

<!-- page -->
# 02  Product purpose and scope

## Problem to solve

Teachers need to control who enters a class, recover from disruption, understand connection history and see whether learning activities reached students. A device left connected provides limited evidence of the learner's participation. Forwarded links, repeated disconnects and ambiguous reports can make classroom management difficult.

## Intended outcomes

- Authorized students can join reliably on supported phones and laptops.
- Teachers can manage entry, student publishing, chat and session completion.
- Attendance records expose measured connection time and uncertainty.
- Polls and short questions provide visible opportunities to participate.
- Institutions manage their own people and records within a clear data boundary.
- Students can understand and request review of records about them.

## Scope by stage

| Stage | Included capability |
| --- | --- |
| Foundation | Responsive shell, configured sign-in path, tenant checks, class planning API, attendance calculation module |
| P0 pilot scope | Institution onboarding, enrollment, live audio/video, waiting room, moderation, event-based attendance, basic polls, teacher reports |
| P1 | CSV imports/exports, reusable learning materials, quizzes, assignments, whiteboard and richer reports |
| P2 | Reviewed AI summaries, recording, breakout rooms, guardian views, optional camera-presence evaluation and native apps |

## Boundaries

ClassGuard reports connection state, submitted answers and other observable events. Mental attention and comprehension require educational judgment. Page visibility may supply disclosed context. Automatic disciplinary decisions, covert monitoring of personal applications and emotion-based student scoring are excluded from the design.

The first pilot targets a small agreed class size and concurrency profile. A proposed starting test envelope is two concurrent classes of 30 learners each. This is a validation target, not a measured capacity or a pricing commitment.

<!-- page -->
# 03  Users and permission model

## Institutional contexts

Schools need supervised access and age-appropriate data handling. Colleges need course rosters, teacher assignments and reviewable attendance. Coaching institutes need recurring batches and quick learning checks. The initial workflow is shared, while policies are configured per institution.

| Role | Permitted scope | Release |
| --- | --- | --- |
| Student | Own timetable, enrollment, submissions, attendance and permitted class material | P0 |
| Teacher | Assigned classes, enrolled learners, moderation, activities and relevant reports | P0 |
| Institution admin | Institution membership, class assignment, policies and institution reports | P0 |
| Principal / HOD | Explicit department or institution reporting scope | P1 |
| Parent / guardian | Explicitly linked child's approved records | P2 |
| Platform operator | Operational metadata and authorized, audited support access | Pilot operations |

## Permission requirements

**ROLE-01 (P0)** - Resolve permissions from server-authoritative institution membership and class assignment. A frontend role label or editable user profile cannot grant authority.

**ROLE-02 (P0)** - A user may belong to multiple institutions. Switching workspace changes the requested scope and triggers a fresh authorization check. It does not carry privileges from the prior institution.

**ROLE-03 (P0)** - Students cannot admit or remove peers, change enrollment, issue media credentials, correct attendance or read other students' private reports.

**ROLE-04 (P0)** - Teachers act on assigned classes. Institution administrators may assign a substitute teacher through an audited operation.

**ROLE-05 (P0)** - Revocation affects new API requests immediately. Realtime and media revocation behavior must be implemented and tested before pilot use.

**ROLE-06 (P2)** - A guardian relationship is verified and revocable. Parent access is limited to approved fields. Support access has an explicit purpose, time limit and audit history.

<!-- page -->
# 04  End-to-end user journeys

## Institution setup

1. A trusted platform operator provisions the institution and first administrator.
2. The administrator configures institution name, timezone and policy values.
3. Teachers and students receive approved accounts and memberships.
4. The administrator assigns courses, teaching responsibilities and rosters.
5. A teacher schedules the first occurrence and validates the join flow with a test learner.

The foundation may use a trusted local provisioning CLI. The pilot requires administrative screens and an invitation lifecycle with expiration, cancellation and duplicate handling.

## Teacher conducts a class

1. Open the scheduled session and test microphone, camera and speaker where supported.
2. Start the actual teaching window and admit eligible students.
3. Share supported media, manage speaking permission and answer raised hands.
4. Launch a poll or question and inspect delivery and submission counts.
5. Record a break or end the session.
6. Review attendance evidence and unresolved connection gaps before finalizing a report.

## Student attends and reconnects

1. Sign in, select the institution and open an enrolled class.
2. Complete prejoin checks and receive the current monitoring/recording notice.
3. Wait for admission where required, then join using a room-specific credential.
4. Answer activities and use accessible text or audio participation paths.
5. On a network interruption, see reconnect status and recover the current activity deadline.
6. After class, view measured attendance and submit a correction request if needed.

## Unauthorized or removed participant

A forwarded link leads through authentication and authorization. An unknown account receives an access-denied state or a policy-defined request flow. A teacher's removal terminates the current connection and blocks new admission for that session. A removal remains effective across refresh, reconnect and cached credentials until explicit re-admission.

<!-- page -->
# 05  Identity and tenant isolation

| ID | Requirement and acceptance condition |
| --- | --- |
| AUTH-01 P0 | Sign-in, sign-out, session expiry and recovery use the approved identity provider. Expired or invalid tokens produce a recoverable authentication state. |
| AUTH-02 P0 | Verify token signature, issuer, audience and expiry on protected API calls. Unconfigured authentication fails closed. |
| AUTH-03 P0 | Private class entry requires active institution membership, enrollment or teacher assignment, permitted session state and admission. |
| AUTH-04 P1 | Institution-configured email OTP or Google sign-in may be added after the base account lifecycle is validated. |
| TEN-01 P0 | Every institution-owned record includes an institution ID. Queries and mutations verify the current user's membership in that institution. |
| TEN-02 P0 | Enforce the same scope for exports, media credentials, realtime channels, background jobs, caches and stored files. |
| TEN-03 P0 | Disable inactive memberships and suspended institutions. Keep a reason and audit record for administrative changes. |
| TEN-04 P1 | Validated CSV import reports per-row errors and supports safe retry without duplicate accounts or memberships. |

## Account identity and verification

An authenticated account identifies the account holder under the institution's onboarding policy. Enrollment verification reduces unauthorized entry. It cannot guarantee that a second person never uses a student's device. Optional higher-assurance verification is a separate requirement with an accessible alternative and a privacy review.

## Tenant acceptance tests

- Changing an institution ID or class ID cannot reveal another institution's data.
- A signed-in student cannot create a class by changing a request payload.
- A teacher cannot access an unassigned class through direct API calls.
- A removed membership cannot obtain new class data or media access.
- A background export and its download use the same authorized scope.

Supabase supports JWT validation and database access policies. The project must validate its own database connection and claims model. API scoping and database row-level security are distinct implementation layers. [S1, S2]

<!-- page -->
# 06  Live classroom and moderation

**ROOM-01 (P0)** - Teachers create, schedule, start and end a session. Store scheduled time separately from actual teaching time. A class supports repeated session occurrences in the integrated MVP.

**ROOM-02 (P0)** - Provide prejoin device selection, microphone/camera controls, participant list, chat and hand raise. Permission denial shows recovery guidance and a supported audio/text path.

**ROOM-03 (P0)** - Use server-enforced admission. Waiting participants receive no live-class media token. Approval binds a specific user and session, expires and is revalidated when redeemed.

**ROOM-04 (P0)** - Teachers can mute participants, restrict publication, disable chat, lock entry, reject a request, remove a participant and end the session. Restoring permission lets the student choose when to activate their device.

**ROOM-05 (P1)** - Screen sharing, presentation files and a collaborative whiteboard require capability detection, role enforcement and tested mobile viewing. Recording and breakout rooms follow separately.

## Admission states

requested -> waiting -> approved -> connected -> disconnected

Terminal or blocking states include rejected, removed, expired and session-ended. Re-admission is an explicit transition. Each command carries an idempotency key or equivalent stable operation ID.

## Required edge-case behavior

| Trigger | Required outcome |
| --- | --- |
| Teacher ends or locks a class during approval | Token redemption rechecks current state and returns a deterministic result |
| Double-clicked admission or repeated request | One resulting transition and one audit event |
| Teacher disconnects | Preserve moderation policy, show recovery status and apply a configured host-recovery policy |
| Student removed with a cached token | Active connection ends and re-entry remains blocked under the chosen media deployment |
| Device change | Explicit transfer policy and stable learner identity; attendance never double-counts |

LiveKit credentials encode identity, room and media grants. Credential expiration and reconnect/revocation behavior must be tested for the chosen deployment. [S3]

<!-- page -->
# 07  Attendance definition and evidence

**ATT-01 (P0)** - Derive attendance from authenticated media-session evidence. Preserve provider event time, receipt time and stable event ID. Verify signatures before processing. Browser timers are supplementary context.

**ATT-02 (P0)** - The counted teaching window runs from the teacher's actual start to actual end. Exclude explicitly recorded breaks. Waiting-room time is reported separately.

**ATT-03 (P0)** - Normalize timestamps to UTC, clip connections to the teaching window, merge overlaps across devices, subtract breaks and sum the remaining confirmed intervals.

`attendance percentage = counted connected seconds / counted teaching seconds x 100`

**ATT-04 (P0)** - A zero counted duration returns no percentage. Missing or unconfirmed exit evidence produces a provisional record requiring reconciliation or review. Network gaps retain their measured duration.

**ATT-05 (P0)** - Corrections preserve the original measurement. Store adjusted status/value, reason, actor and time. Students can request review. Institution attendance thresholds and late-entry rules are configurable and validated before pilot.

| Scenario | Required result |
| --- | --- |
| Connected 10:00-10:30 and 10:40-11:00 | 50 minutes, 83.33% of a 60-minute class |
| Devices overlap 10:00-10:40 and 10:20-11:00 | 60 minutes, maximum 100% |
| Waiting five minutes, connected for 55 | 55 counted minutes |
| Teacher ends at 10:45 | Actual 45-minute denominator |
| A recorded 10-minute break in a 60-minute class | Break removed from numerator and denominator |
| Duplicate or reordered events | Same finalized interval set and result |

An optional reconnect grace period may display "Reconnecting" before "Disconnected". It must not silently credit missing connection time. The foundation calculator is independent of the future ingestion and reconciliation pipeline.

<!-- page -->
# 08  Participation and context indicators

## Observable learning activities

**ENG-01 (P0)** - A teacher can launch a poll or quick question with a target audience, open time and deadline. Students receive accessible text and a clear submission state.

**ENG-02 (P0)** - Persist one effective response per student/activity with a stable submission ID and server timestamp. A retry must not create another response or extend its deadline.

**ENG-03 (P0)** - Distinguish answered, delivered-but-unanswered, not-delivered, excused and submitted-late states. Reconnection restores the active question and remaining server-calculated time.

**ENG-04 (P0)** - Define eligibility from targeting, confirmed delivery and adequate response opportunity. The proposed minimum response window is 30 seconds, subject to institution policy and accommodations.

`participation rate = submitted eligible activities / eligible activities`

Display the counts, such as "4 of 5 eligible activities". Zero eligible activities displays "Not enough activity data". Quiz accuracy is calculated separately. An incorrect answer still counts as a submitted response.

## Teacher interpretation

Present attendance, activity responses, quiz accuracy and connection quality as separate measures. Hand raises and chat contributions can appear as events. Avoid rewarding message volume or combining weak signals into an unexplained attention score.

## Optional page-visibility context

**ENG-05 (P1)** - When enabled, disclose collection of the classroom document's visible/hidden state and duration. Record only the data needed for that purpose. Let students inspect the signal and add context.

Browsers may throttle timers or suspend pages. Visibility cannot identify the other application, establish off-task behavior or determine comprehension. Opening course material and using accessibility tools are legitimate reasons for a state change. Visibility must not independently determine attendance, grades or discipline. [S4]

**ENG-06 (P1)** - Random checks use a disclosed activity policy and accessible response paths. Evaluate whether they improve classroom interaction during the pilot before increasing frequency.

<!-- page -->
# 09  Dashboards and learning extensions

| Experience | P0 capability | Subsequent scope |
| --- | --- | --- |
| Student | Timetable, class access, activities, own attendance and review request | Assignments, revision material and progress history |
| Teacher | Today's sessions, waiting room, moderation, attendance evidence and poll results | Course trends, richer assessment and exports |
| Institution admin | Users, memberships, rosters, teacher assignment and audit view | Imports, policy dashboards and operational reports |
| Principal / HOD | Explicit reporting scope after core roles | Department trends and approved exports |
| Parent / guardian | Separate later release | Linked child's institution-approved records |

## Assessments and materials

**LEARN-01 (P1)** - Teachers create MCQ quizzes and assignments with availability, due date and submission rules. Validate file type/size, preserve upload failures and distinguish uploaded from submitted.

**LEARN-02 (P1)** - Automatically score objective questions against a versioned answer key. Descriptive work is teacher-reviewed. Preserve the question version used for each submission.

**LEARN-03 (P1)** - Class materials are accessed through authorized URLs. A copied download link expires or rechecks access. File scanning and retention are pilot requirements before accepting student uploads.

## AI classroom assistant

**AI-01 (P2)** - Generate summaries, key topics and revision questions from institution-approved transcripts or material. Label generated content, retain source references and allow teacher editing before release.

**AI-02 (P2)** - Evaluate factuality, source grounding and correction rates on representative teaching material. Teacher review remains required for published learning content and assessment answer keys.

**AI-03 (P2)** - Recording, transcription and external AI processing each need an explicit policy, notice, retention period and approved provider configuration. Cost and usage limits are deployment decisions.

Optional camera-presence experiments require a separate evaluation and accessible alternatives. Face direction, facial expressions and camera availability do not provide a basis for emotion, misconduct or attention determinations.

<!-- page -->
# 10  Mobile, PWA and accessibility

## Supported experience

The first client is a responsive browser application. Validate core flows on current supported Chrome, Edge, Firefox and Safari, with real-device checks for Android and iPhone/iPad. Record exact tested versions in each release report.

| ID | Acceptance requirement |
| --- | --- |
| UX-01 P0 | Core navigation, prejoin, chat and activities work at phone, tablet and desktop widths without horizontal page scrolling. |
| UX-02 P0 | Touch controls remain usable in portrait/landscape and respect safe areas. Rotating the device preserves the active session. |
| UX-03 P0 | Offer audio-only participation, adaptive video and visible reconnect status. A permission denial has a usable recovery path. |
| A11Y-01 P0 | Keyboard navigation, visible focus, meaningful labels and readable contrast cover every core action. |
| A11Y-02 P0 | Activity timing supports accommodations. Status changes are announced appropriately to assistive technology. |
| A11Y-03 P1 | Captions/transcripts follow the selected service's supported capabilities, with availability clearly shown. |
| PWA-01 P1 | Provide manifest, suitable icons and supported installation behavior. Installation remains optional. |

## Browser capability requirements

Detect screen-capture capability and show an explicit unavailable state when needed. Publishing a screen and receiving a teacher's shared screen are distinct capabilities. System audio sharing needs a separate check. Permission to share is requested through the browser's normal user-initiated flow. [S5]

Background lifecycle behavior varies by browser and OS. Restore state from server timestamps after resume. Do not use repeated local timer callbacks to establish attendance or assessment deadlines. [S4]

## Offline and notifications

Cache only an approved app shell and explicitly chosen study material. Protected API responses, credentials and meeting media must not be cached by the service worker. A queued action remains visibly pending until acknowledged by the server. Live calls require connectivity.

Push notifications depend on browser support, installation state and permission. Preserve in-app reminders when push is unavailable. An installable shortcut does not establish native background capabilities. [S6, S7]

<!-- page -->
# 11  Architecture and implementation choices

[[architecture]]

## Technology direction

| Layer | Choice | Boundary |
| --- | --- | --- |
| Web client | Next.js, React, TypeScript | Responsive interface and browser permissions |
| UI foundation | Plain CSS initially | Documented simplification; component system can evolve |
| API | Python FastAPI | Authentication verification and business authorization |
| Database | PostgreSQL for deployment | SQLite supports local foundation development |
| Identity | Supabase Auth | Account lifecycle; institution authority stays in the application |
| Media | LiveKit | Audio/video/screenshare transport after admission |
| App events | Server API plus realtime delivery | Durable records and authorized event subscriptions |
| Background work | Queue/worker when introduced | Reports, reconciliation, transcription and AI jobs |

The API owns teaching assignments, enrollment and policy. The client requests actions and displays results. Media transport stays separate from educational records so event calculations remain testable.

Production requires HTTPS, configured identity and media services, database migrations, backups and monitoring. SQLite tests do not prove PostgreSQL isolation or production capacity. A local UI preview is explicitly labeled and separated from authenticated data.

<!-- page -->
# 12  Logical data model

Every institution-owned record carries `institution_id`. Use opaque IDs for public resources and media identities. Store timestamps in UTC and display the institution/user timezone explicitly.

| Entity | Key relationships and fields |
| --- | --- |
| Institution | Name, active state, timezone and policy version |
| User / Membership | Identity-provider user ID; institution, role, active state |
| Course / Classroom | Institution, subject, assigned teachers and reusable class definition |
| Enrollment | Institution, classroom and student; effective membership status |
| ClassSession | Classroom occurrence; scheduled/actual time, lifecycle, policy snapshot |
| Admission | Session, user, state, approver, expiration and operation ID |
| ProviderEvent | Provider/event unique key, session, raw payload reference, event/receipt time and processing state |
| ConnectionInterval | Session, learner, connection/device reference, start/end and confirmation status |
| AttendanceRecord | Measured seconds, denominator, percentage, review state and calculation version |
| AttendanceCorrection | Original/adjusted value, reason, actor and timestamp |
| Activity / Delivery | Versioned question, targets, open/deadline, delivery evidence |
| Submission | Activity, learner, answer, stable submission ID and server timestamp |
| AuditEvent | Actor, institution, action, resource, result and timestamp |

## Integrity and evolution

Use foreign keys and uniqueness constraints for memberships, enrollments, event deduplication and submissions. Composite tenant/resource constraints reduce accidental cross-tenant links. Authorization still checks the active caller's scope.

The foundation stores a scheduled class record. The integrated MVP separates reusable classrooms from individual session occurrences before recurring lessons and session attendance are introduced.

Schema changes use versioned migrations. Retain calculation and policy versions so a report can be explained after logic changes. Restrict access to raw events and retain them only under an agreed evidence/retention policy.

<!-- page -->
# 13  API and event contracts

## Foundation API

| Route | Contract |
| --- | --- |
| GET /health | Service health response without protected records |
| GET /v1/capabilities | Configuration and implemented-feature status |
| GET /v1/me | Verified user and active institution memberships |
| GET /v1/institutions/{id}/classes | Role-scoped list; admin institution scope, teacher owned classes, student enrollments |
| POST /v1/institutions/{id}/classes | Authorized admin/teacher creates validated scheduled class |

Class creation accepts title, subject, optional description, timezone-aware start time and duration. The current foundation range is 5-480 minutes. That input range is a validation boundary, not a recommended teaching duration.

## Next API groups

- Session lifecycle and idempotent start/end actions.
- Admission requests, approval, rejection and secure media-token issue.
- Enrollment and teaching-assignment administration.
- Activities, delivery acknowledgments and retry-safe submissions.
- Attendance evidence, corrections and authorized exports.

Error responses distinguish unauthenticated, unauthorized/not-found, validation failure, conflicting state, rate limit and temporary service failure. Avoid revealing resource existence across institution boundaries.

## Durable event requirements

**EVENT-01 (P0)** - Verify provider webhook signatures using the raw request. Record a provider/event unique key and acknowledge only after durable receipt.

**EVENT-02 (P0)** - Preserve both event time and receipt time. Repeated or reordered delivery must converge on one authoritative result. Quarantine malformed events for operator review.

**EVENT-03 (P0)** - Reconcile incomplete intervals after disconnects, provider gaps or server restarts. Reports remain provisional while evidence is unresolved.

**EVENT-04 (P0)** - Realtime subscriptions validate membership and session scope. Reconnect obtains a current snapshot and resumes from a cursor or equivalent version.

<!-- page -->
# 14  Privacy and security requirements

## Data collection and control

**PRIV-01 (P0)** - Explain each collected data category, its purpose, viewers and retention before collection. Provide a student-facing view of attendance and participation evidence.

**PRIV-02 (P0)** - Request camera/microphone access through standard browser prompts. Optional signals require visible controls and an equivalent participation path for students who cannot use them.

**PRIV-03 (P0)** - Define retention and deletion for attendance, activity responses, chat, audit evidence and files. Recording/transcript retention is a separate later decision. Record deletion outcomes and any required retention exception.

**PRIV-04 (P0)** - Validate institution responsibilities, minor/guardian workflows, region and applicable requirements with qualified reviewers before onboarding school-age users. This PRD does not establish legal compliance.

## Security controls

- TLS for external connections and appropriately configured encryption at rest.
- Least-privilege service accounts and secret storage outside browser bundles and Git.
- Server-side membership checks, validated inputs and explicit CORS origins.
- Rate limits for sign-in-adjacent operations, admission and chat when those routes ship.
- Audit membership changes, admission/removal, corrections, exports and policy changes.
- Avoid access tokens, credentials and unnecessary student data in logs.
- Restrict file downloads, validate uploads and introduce scanning before accepting attachments.
- Backup and restore procedures with authorized access and a tested recovery path.

## High-impact educational decisions

Attendance adjustments, grades and disciplinary decisions require authorized human review under institutional policy. The product displays measured evidence and uncertainty. It does not determine misconduct or mental attention from facial expressions, head orientation, camera status or hidden tabs.

Raw face templates, identity biometrics and emotion models are outside the initial release. Any future biometric identity proposal requires a distinct justification, validation, alternatives, retention model and review before implementation.

<!-- page -->
# 15  Quality targets and success measures

The following targets guide testing. They are proposed service objectives and require measurement before being represented as achieved.

| Area | Initial acceptance target |
| --- | --- |
| Standard API performance | p95 under 500 ms under the agreed pilot load, with the endpoint mix and network conditions recorded |
| Availability | Proposed initial objective 99.5%; define measured boundary, maintenance and third-party treatment before pilot |
| Join reliability | Track authorized join success and failure causes on real devices |
| Tenant isolation | All defined cross-tenant negative tests pass before release |
| Accessibility | Core tasks complete by keyboard; readable contrast, focus and assistive labels reviewed |
| Recovery | Reconnect and worker restart recover durable state without duplicate responses or inflated attendance |
| Operations | Health/error metrics, accountable incident owner and tested database restore |

## Product metrics

| Metric | Operational definition |
| --- | --- |
| Authorized join success | Successful media joins / eligible authorized join attempts; separate user cancellation |
| Attendance completeness | Finalized session reports with reconciled evidence / sessions requiring reports |
| Activity participation | Submitted eligible activities / eligible activities, with visible counts |
| Teacher task success | Teachers completing start, moderation and report review tasks without assistance |
| Classroom disruption | Reported/moderation incidents per class hour, interpreted with context |
| Mobile task success | Completed join/activity/recovery tasks by tested browser/device combination |

Collect a pilot baseline before setting improvement claims. Report small sample sizes and service outages alongside results. Student camera-on time and number of flags are not standalone product success measures.

## Cost visibility

Measure participant-minutes, media egress, storage, transcription and AI usage when enabled. Establish institutional budgets and alerts before paid deployment. Pricing and subscriptions follow customer validation.

<!-- page -->
# 16  Open-source reference assessment

Review baseline 03 November 2026. The implementation should adopt components only after an exact version, applicable license, notices, dependencies and validation record are documented.

| Reference | Observed root license | Intended use |
| --- | --- | --- |
| LiveKit Meet | Apache-2.0 | Prejoin, device controls and conferencing UI reference [R1] |
| LiveKit Components JS | Apache-2.0 | Candidate reusable React media components [R2] |
| LiveKit Server | Apache-2.0 | Candidate WebRTC media infrastructure [R3] |
| BigBlueButton | LGPL-3.0 | Education workflows and separately evaluated integration [R4] |
| Jitsi Meet | Apache-2.0 | Conferencing architecture reference [R5] |
| MediaPipe | Apache-2.0 | Optional future on-device perception evaluation [R6] |

## Exact prototypes in the supplied PRD

**Yuga-04/AI-Classroom-Monitor [R7]** - Inspected default branch `yugu`. The root LICENSE was unavailable and repository license metadata was null. The source is a camera/analysis prototype. Keep it as a research reference until reuse permissions are established.

**Sumant3086/ProxyMukt-Attendance-System- [R8]** - README states and reproduces MIT terms, while the linked root LICENSE was unavailable. Attendance/identity workflow ideas may inform research. Record license/provenance review as pending before importing source.

**reevon-dsouza/AI-Assisted-classroom-monitoring [R9]** - No named reuse license was confirmed. Required custom weights and face data are excluded. Code and model terms need clarification before adoption.

A repository's claimed detection features do not establish real-world accuracy. This project uses observable attendance and participation requirements. Prototype emotion or cheating labels are not adopted as educational measures.

Full reviewed revisions and evidence are recorded in `docs/OPEN_SOURCE_REVIEW.md`. Root-license observations do not cover every dependency, model, asset or hosted service. The three prototypes have not been imported into the foundation.

<!-- page -->
# 17  Delivery plan and acceptance gates

| Milestone | Deliverable | Exit evidence |
| --- | --- | --- |
| Foundation | Responsive shell, identity integration path, class planning API, attendance algorithm | Build/typecheck, authorization tests and algorithm cases; clear configuration states |
| MVP 0.1 | Onboarding, roles, enrollment, class/session model | Admin configures institution; teacher schedules; student sees correct roster-based timetable |
| MVP 0.2 | LiveKit, admission and moderation | Real two-device call; remove/rejoin, lock/end and device-denial cases pass |
| MVP 0.3 | Event pipeline, attendance, corrections | Duplicate/reordered/missing events reconcile; corrections retain audit history |
| MVP 0.4 | Polls, questions and participation | Delivery states, deadlines and retry-safe responses work after reconnect |
| Pilot | Security, mobile QA, operations and policies | Signed institutional acceptance, measured load test and documented service limits |

## Required acceptance cases

1. An enrolled student joins the correct class; a forwarded link cannot bypass authorization.
2. A student cannot obtain teacher authority, remove peers or publish a forbidden screen track.
3. Tenant A cannot access tenant B records through API, downloads or realtime channels.
4. Removal remains effective after refresh and reconnect with cached credentials.
5. Attendance handles overlaps, breaks, disconnections, early endings and uncertain exits.
6. A repeated activity submission creates one response and retains the server deadline.
7. Camera denial preserves an appropriate supported audio/text path.
8. Teacher corrections show original evidence, reason, actor and time.
9. Students can inspect their records and request review.
10. Real mobile and desktop devices complete join, activity, rotation and recovery tests.

Each milestone may be demonstrated locally before deployment. An institutional pilot additionally requires configured services, approved operating policies and accountable support. UI completion alone does not establish live classroom readiness.

<!-- page -->
# 18  Risks, decisions and change control

| Risk | Mitigation and release condition |
| --- | --- |
| Unstable mobile/background behavior | Feature detection, real-device matrix, reconnect recovery and uncertainty labels |
| Incorrect attendance after network failure | Verified intervals, reconciliation, correction workflow and evidence retention |
| Cross-tenant exposure | Central scope checks, constraints, negative tests and production database validation |
| Removed user re-enters | Test actual provider revocation/reconnect behavior; block credentials and terminate connection |
| Overstated engagement signals | Separate observable measures, visible denominators and human review |
| Unclear prototype licensing | Hold source/model reuse until exact permissions and notices are established |
| Uncontrolled operating cost | Pilot capacity, usage limits, service budgets and alerts |

## Open decisions before pilot

- Identify the pilot institution, accountable product owner and support contact.
- Confirm class size, concurrent sessions and expected device/network profile.
- Select LiveKit Cloud or self-hosting, deployment region and database hosting.
- Set attendance threshold, late-entry policy, teacher correction authority and appeal process.
- Define retention, recording/transcript policy, student notices and minor/guardian workflows.
- Confirm invitation, account recovery, substitute-teacher and device-transfer policies.
- Agree pilot acceptance metrics, cost budget and production readiness review.

## Change control

Record any change to MVP scope, data collection, monitoring behavior, permissions or metric definitions in an architecture/product decision entry. Include rationale, affected requirements, migration impact and updated acceptance evidence.

The next implementation sequence is institution onboarding and enrollment, reusable classroom/session modeling, server-enforced admission, LiveKit integration, verified events, then attendance reporting and activities. AI learning assistance follows validated classroom workflows and approved data handling.

<!-- page -->
# 19  Primary sources and reference links

Sources were reviewed for the engineering plan on 03-04 November 2026. These links support implementation context. Product policies and targets in this PRD are proposed requirements.

## Platform documentation

- **S1** - Supabase JWT verification. [supabase.com/docs/guides/auth/jwts](https://supabase.com/docs/guides/auth/jwts)
- **S2** - Supabase row-level security. [supabase.com/docs/guides/database/postgres/row-level-security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- **S3** - LiveKit access tokens and grants. [docs.livekit.io/frontends/reference/tokens-grants](https://docs.livekit.io/frontends/reference/tokens-grants/)
- **S4** - MDN Page Visibility API. [developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API](https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API)
- **S5** - MDN display capture. [developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia)
- **S6** - Next.js PWA guide. [nextjs.org/docs/app/guides/progressive-web-apps](https://nextjs.org/docs/app/guides/progressive-web-apps)
- **S7** - Apple web push guidance. [Apple web-app and browser push documentation](https://developer.apple.com/documentation/usernotifications/sending-web-push-notifications-in-web-apps-and-browsers)

## Repositories

- **R1** - [LiveKit Meet](https://github.com/livekit-examples/meet)
- **R2** - [LiveKit Components JS](https://github.com/livekit/components-js)
- **R3** - [LiveKit Server](https://github.com/livekit/livekit)
- **R4** - [BigBlueButton](https://github.com/bigbluebutton/bigbluebutton)
- **R5** - [Jitsi Meet](https://github.com/jitsi/jitsi-meet)
- **R6** - [MediaPipe](https://github.com/google-ai-edge/mediapipe)
- **R7** - [Yuga-04 AI Classroom Monitor](https://github.com/Yuga-04/AI-Classroom-Monitor)
- **R8** - [ProxyMukt Attendance System](https://github.com/Sumant3086/ProxyMukt-Attendance-System-)
- **R9** - [AI-Assisted Classroom Monitoring](https://github.com/reevon-dsouza/AI-Assisted-classroom-monitoring)

**Document baseline** - The user's original PRD v1.0 is preserved alongside this revision. Engineering refinements should be reviewed with the pilot institution before policy defaults are finalized.
