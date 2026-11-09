"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { API_URL } from "@/lib/api";
import { authConfigured } from "@/lib/supabase";
import type { ClassPlan, PageName } from "@/lib/types";
import { useApp } from "./app-provider";
import { BrandMark, Icon, type IconName } from "./icons";
import { CreateClassModal, SignInModal } from "./forms";
import { Modal } from "./modal";
import { InstitutionSetup, JoinInstitution } from "./onboarding";
import { People } from "./people";
import { ClassEnrollment } from "./class-enrollment";

const navigation: {
  page: PageName;
  label: string;
  path: string;
  icon: IconName;
}[] = [
  { page: "dashboard", label: "Dashboard", path: "/", icon: "dashboard" },
  { page: "classes", label: "Classes", path: "/classes", icon: "classes" },
  { page: "people", label: "People", path: "/people", icon: "users" },
  {
    page: "attendance",
    label: "Attendance",
    path: "/attendance",
    icon: "attendance",
  },
  { page: "setup", label: "Setup", path: "/setup", icon: "setup" },
];

function previewClasses(): ClassPlan[] {
  const today = new Date();
  today.setHours(9, 0, 0, 0);
  return [
    {
      title: "The science of everyday motion",
      subject: "Physics",
      description:
        "Explore forces and motion through real-world examples, then work through a short problem-solving activity.",
      hour: 9,
      duration: 45,
    },
    {
      title: "Finding patterns in algebra",
      subject: "Mathematics",
      description:
        "Connect visual patterns to algebraic expressions and compare different ways to solve the same problem.",
      hour: 11,
      duration: 60,
    },
    {
      title: "Stories that change perspectives",
      subject: "English",
      description:
        "Discuss point of view, choose supporting evidence, and develop an interpretation of a short text.",
      hour: 14,
      duration: 45,
    },
  ].map((item, index) => {
    const start = new Date(today);
    start.setHours(item.hour);
    return {
      id: `preview-${index}`,
      institution_id: "preview",
      title: item.title,
      subject: item.subject,
      description: item.description,
      starts_at: start.toISOString(),
      duration_minutes: item.duration,
      created_by: "preview",
      created_at: today.toISOString(),
    };
  });
}

function formatDate(value: string, withDate = false) {
  return new Intl.DateTimeFormat(undefined, {
    ...(withDate ? ({ month: "short", day: "numeric" } as const) : {}),
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function ClassroomIllustration() {
  return (
    <div className="hero-illustration" aria-hidden="true">
      <div className="orbit orbit-one" />
      <div className="orbit orbit-two" />
      <div className="floating-note note-one">
        <Icon name="book" size={19} />
        <span>
          Make space
          <br />
          <b>for learning.</b>
        </span>
      </div>
      <div className="illustration-board">
        <div className="board-top">
          <span />
          <span />
          <span />
        </div>
        <div className="board-body">
          <div className="board-symbol">
            Aa<span>+</span>
          </div>
          <div className="board-lines">
            <i />
            <i />
            <i />
          </div>
        </div>
        <div className="board-person person-a">A</div>
        <div className="board-person person-b">M</div>
        <div className="board-person person-c">S</div>
        <div className="board-person person-d">
          <Icon name="plus" size={14} />
        </div>
      </div>
      <div className="floating-check">
        <Icon name="spark" size={25} />
      </div>
    </div>
  );
}

export function Workspace({ page }: { page: PageName }) {
  const app = useApp();
  const [signInOpen, setSignInOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedClass, setSelectedClass] = useState<ClassPlan | null>(null);
  const [query, setQuery] = useState("");
  const [notice, setNotice] = useState("");
  const [date, setDate] = useState("");
  const samples = useMemo(previewClasses, []);
  const visibleClasses = app.preview ? samples : app.classes;
  const filteredClasses = visibleClasses.filter((item) =>
    `${item.title} ${item.subject}`
      .toLocaleLowerCase()
      .includes(query.toLocaleLowerCase()),
  );
  const canCreate = Boolean(
    !app.preview &&
      app.session &&
      app.institution &&
      ["admin", "teacher"].includes(app.institution.role),
  );
  const readySteps = [
    authConfigured,
    app.apiStatus === "online",
    Boolean(app.session),
    Boolean(app.institution),
  ].filter(Boolean).length;

  useEffect(() => {
    setDate(
      new Intl.DateTimeFormat(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
      }).format(new Date()),
    );
  }, []);
  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(""), 6000);
    return () => window.clearTimeout(timeout);
  }, [notice]);
  useEffect(() => {
    setSelectedClass(null);
    setCreateOpen(false);
    setNotice("");
  }, [app.session?.user.id, app.institution?.institution_id, app.preview]);

  function classButton() {
    if (canCreate)
      return (
        <button className="button primary" onClick={() => setCreateOpen(true)}>
          <Icon name="plus" size={18} />
          Plan a class
        </button>
      );
    if (!app.session && !app.preview)
      return (
        <button className="button primary" onClick={() => setSignInOpen(true)}>
          <Icon name="lock" size={17} />
          Sign in
        </button>
      );
    return (
      <Link href="/setup" className="button secondary">
        <Icon name="setup" size={17} />
        View setup
      </Link>
    );
  }

  function classList() {
    if (
      !app.preview &&
      (app.authLoading || app.profileLoading || app.classesLoading)
    )
      return (
        <div className="loading-state" role="status">
          <span className="spinner" />
          Loading your classes…
        </div>
      );
    if (!app.preview && app.classesError)
      return (
        <div className="error-state" role="alert">
          <b>Classes could not be loaded</b>
          <p>{app.classesError}</p>
          <button
            className="button secondary small"
            onClick={app.refreshClasses}
          >
            Try again
          </button>
        </div>
      );
    if (!filteredClasses.length)
      return (
        <div className="empty-state">
          <div className="empty-icon">
            <Icon name={query ? "search" : "classes"} size={32} />
          </div>
          <h3>
            {query ? "No matching classes" : "Your next chapter starts here"}
          </h3>
          <p>
            {query
              ? "Try another class title or subject."
              : app.institution
                ? "Class plans will appear here. Your institution controls which classes you can access."
                : "Connect your institution and sign in to see your classes. You can explore the design while setup is in progress."}
          </p>
          {query ? (
            <button className="button secondary" onClick={() => setQuery("")}>
              Clear search
            </button>
          ) : canCreate ? (
            <button
              className="button primary"
              onClick={() => setCreateOpen(true)}
            >
              <Icon name="plus" size={17} />
              Plan your first class
            </button>
          ) : (
            <button
              className="button secondary"
              onClick={() => app.setPreview(true)}
            >
              <Icon name="eye" size={18} />
              Explore design preview
            </button>
          )}
        </div>
      );
    return (
      <div className="class-list">
        {filteredClasses.map((item, index) => (
          <button
            key={item.id}
            className="class-card"
            onClick={() => setSelectedClass(item)}
          >
            <div className={`subject-mark subject-${index % 3}`}>
              <Icon
                name={
                  index % 3 === 0
                    ? "spark"
                    : index % 3 === 1
                      ? "classes"
                      : "book"
                }
                size={24}
              />
            </div>
            <div className="class-info">
              <div className="class-meta">
                <span>{item.subject}</span>
                <span className="tag">
                  {app.preview ? "Sample" : "Class plan"}
                </span>
              </div>
              <h3>{item.title}</h3>
              <div className="class-timing">
                <span>
                  <Icon name="calendar" size={14} />
                  {formatDate(item.starts_at, true)}
                </span>
                <span>
                  <Icon name="clock" size={14} />
                  {item.duration_minutes} min
                </span>
              </div>
            </div>
            <span className="class-arrow">
              <Icon name="arrow" size={20} />
            </span>
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="ClassGuard AI dashboard">
          <BrandMark />
          <span>
            ClassGuard<span className="brand-ai">AI</span>
          </span>
        </Link>
        <div className="workspace-label">LEARNING WORKSPACE</div>
        <nav aria-label="Main navigation">
          {navigation.map((item) => (
            <Link
              key={item.page}
              href={item.path}
              className={`nav-item ${page === item.page ? "active" : ""}`}
              aria-current={page === item.page ? "page" : undefined}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {item.page === "attendance" && <small>SOON</small>}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="foundation-card">
            <div className="foundation-icon">
              <Icon name="spark" size={20} />
            </div>
            <b>A thoughtful start.</b>
            <p>Your classroom foundation is taking shape.</p>
            <Link href="/setup">
              See what’s ready <Icon name="arrow" size={15} />
            </Link>
          </div>
          <div className="sidebar-foot">
            <span className="status-dot" />
            Community · v0.2
          </div>
        </div>
      </aside>

      <div className="workspace-main">
        <header className="topbar">
          <div className="institution-control">
            <span className="institution-icon">
              <Icon name="book" size={20} />
            </span>
            {app.preview ? (
              <div>
                <b>Design preview</b>
                <span>Sample classroom workspace</span>
              </div>
            ) : app.profile?.memberships.length ? (
              <label className="institution-select">
                <span className="sr-only">Institution</span>
                <select
                  value={app.institution?.institution_id || ""}
                  onChange={(event) => app.setInstitutionId(event.target.value)}
                >
                  {app.profile.memberships.map((item) => (
                    <option
                      key={item.institution_id}
                      value={item.institution_id}
                    >
                      {item.institution_name}
                    </option>
                  ))}
                </select>
                <small>{app.institution?.role} workspace</small>
              </label>
            ) : (
              <div>
                <b>Your institution</b>
                <span>
                  {app.session ? "Membership required" : "Ready when you are"}
                </span>
              </div>
            )}
          </div>
          <div className="topbar-actions">
            <span className={`connection-badge ${app.apiStatus}`}>
              <span />
              {app.apiStatus === "online"
                ? "API online"
                : app.apiStatus === "checking"
                  ? "Checking API"
                  : "API unavailable"}
            </span>
            <span className="topbar-divider" />
            {app.session ? (
              <button
                className="profile-button"
                onClick={app.signOut}
                title="Sign out"
                aria-label="Sign out"
              >
                <span className="avatar">
                  {(app.profile?.email ||
                    app.session.user.email ||
                    "U")[0].toUpperCase()}
                </span>
                <span>Sign out</span>
                <Icon name="logout" size={17} />
              </button>
            ) : (
              <button
                className="profile-button"
                onClick={() => setSignInOpen(true)}
                aria-label="Sign in"
              >
                <span className="avatar">
                  <Icon name="users" size={17} />
                </span>
                <span>Sign in</span>
              </button>
            )}
          </div>
        </header>

        {app.preview && (
          <div className="preview-banner">
            <span>
              <Icon name="eye" size={17} />
              <b>Design preview</b>
              <span>
                Sample classes only. Live services and security checks are
                inactive.
              </span>
            </span>
            <button
              onClick={() => {
                app.setPreview(false);
                setQuery("");
                setSelectedClass(null);
              }}
            >
              Exit preview <Icon name="close" size={15} />
            </button>
          </div>
        )}

        <main id="main-content" className="page-content">
          {app.authError && (
            <div className="notice error" role="alert">
              {app.authError}
            </div>
          )}
          {app.profileError && (
            <div className="notice error" role="alert">
              <span>
                We couldn’t load your institution access. {app.profileError}
              </span>
              <button onClick={app.refresh}>Retry</button>
            </div>
          )}
          {notice && (
            <div className="notice success" role="status">
              <Icon name="check" size={18} />
              {notice}
            </div>
          )}

          {page === "dashboard" && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">YOUR CLASSROOM, CONNECTED</div>
                  <h1>A good day to learn.</h1>
                  <p>A little structure. More room for every student.</p>
                </div>
                <div className="date-label">
                  <Icon name="calendar" size={16} />
                  {date || "Your workspace"}
                </div>
              </div>
              <section className="welcome-hero">
                <div className="hero-copy">
                  <span className="hero-kicker">
                    <span />
                    Built around learning
                  </span>
                  <h2>
                    Great classes begin
                    <br />
                    with a clear plan.
                  </h2>
                  <p>
                    Bring your schedule, classroom access, and learning tools
                    into one considered space.
                  </p>
                  <div className="hero-actions">
                    {classButton()}
                    <button
                      className="text-button"
                      onClick={() => app.setPreview(!app.preview)}
                    >
                      {app.preview
                        ? "Return to workspace"
                        : "Explore the design"}
                      <Icon name="arrow" size={17} />
                    </button>
                  </div>
                </div>
                <ClassroomIllustration />
              </section>

              {!app.institution && (
                <InstitutionSetup onSignIn={() => setSignInOpen(true)} />
              )}

              <section className="stats-grid" aria-label="Workspace overview">
                <div className="stat-card">
                  <span className="stat-icon green">
                    <Icon name="classes" />
                  </span>
                  <div>
                    <span>
                      {app.preview
                        ? "Sample class plans"
                        : "Accessible class plans"}
                    </span>
                    <strong>
                      {app.preview
                        ? samples.length
                        : app.institution && !app.classesError
                          ? app.classes.length
                          : "—"}
                    </strong>
                    <small>
                      {app.preview
                        ? "Explore example lessons"
                        : app.institution
                          ? "From your institution"
                          : "Available after sign-in"}
                    </small>
                  </div>
                </div>
                <div className="stat-card">
                  <span className="stat-icon lavender">
                    <Icon name="attendance" />
                  </span>
                  <div>
                    <span>Attendance</span>
                    <strong className="stat-word">Planned</strong>
                    <small>Service integration pending</small>
                  </div>
                </div>
                <div className="stat-card">
                  <span className="stat-icon peach">
                    <Icon name="setup" />
                  </span>
                  <div>
                    <span>Workspace setup</span>
                    <strong>
                      {readySteps}
                      <em>/ 4</em>
                    </strong>
                    <small>Connection steps complete</small>
                  </div>
                </div>
              </section>

              <div className="dashboard-grid">
                <section className="panel classes-panel">
                  <div className="section-heading">
                    <div>
                      <h2>
                        {app.preview
                          ? "A day in your classroom"
                          : "Your class plans"}
                      </h2>
                      <p>
                        {app.preview
                          ? "A sample schedule to explore the experience."
                          : "All your accessible lessons, in one place."}
                      </p>
                    </div>
                    <Link href="/classes" className="text-link">
                      View all <Icon name="arrow" size={16} />
                    </Link>
                  </div>
                  {classList()}
                </section>
                <aside className="getting-ready panel">
                  <div className="section-heading">
                    <h2>Getting ready</h2>
                    <span className="mini-count">{readySteps}/4</span>
                  </div>
                  <p className="muted">
                    Connect the essentials to start planning classes.
                  </p>
                  <SetupSteps compact />
                  <Link href="/setup" className="button secondary full">
                    Continue setup
                    <Icon name="arrow" size={17} />
                  </Link>
                  <div className="privacy-note">
                    <Icon name="lock" size={16} />
                    <p>
                      Your institution memberships determine access to class
                      plans.
                    </p>
                  </div>
                </aside>
              </div>
            </>
          )}

          {page === "classes" && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">A SPACE FOR EVERY SUBJECT</div>
                  <h1>Your classes.</h1>
                  <p>
                    {app.preview
                      ? "Explore sample class plans in this local design preview."
                      : "Plan lessons and find the classes your institution has shared with you."}
                  </p>
                </div>
                {classButton()}
              </div>
              <section className="panel">
                <div className="class-toolbar">
                  <div className="section-heading">
                    <h2>{app.preview ? "Sample classes" : "Class plans"}</h2>
                    <span className="count-pill">{visibleClasses.length}</span>
                  </div>
                  <label className="search-field">
                    <Icon name="search" size={18} />
                    <span className="sr-only">Search classes</span>
                    <input
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="Search title or subject"
                    />
                  </label>
                </div>
                {classList()}
              </section>
              <div className="service-note">
                <Icon name="video" size={20} />
                <p>
                  <b>Class planning is the first step.</b> Live classrooms,
                  verified entry, and classroom controls are scheduled for later
                  development.
                </p>
              </div>
            </>
          )}

          {page === "people" && <People onSignIn={() => setSignInOpen(true)} />}
          {page === "join" && <JoinInstitution />}

          {page === "attendance" && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">UNDERSTAND PARTICIPATION</div>
                  <h1>Attendance, with context.</h1>
                  <p>
                    A dedicated space for attendance records when the classroom
                    service is ready.
                  </p>
                </div>
                <span className="stage-tag">Planned feature</span>
              </div>
              <section className="attendance-hero panel">
                <div className="attendance-art" aria-hidden="true">
                  <div className="attendance-sheet">
                    <div className="sheet-title" />
                    <div className="sheet-row">
                      <i />
                      <span />
                      <b />
                    </div>
                    <div className="sheet-row">
                      <i />
                      <span />
                      <b />
                    </div>
                    <div className="sheet-row">
                      <i />
                      <span />
                      <b />
                    </div>
                    <div className="sheet-row">
                      <i />
                      <span />
                      <b />
                    </div>
                  </div>
                  <span className="attendance-bubble">
                    <Icon name="attendance" size={30} />
                  </span>
                </div>
                <div>
                  <span className="eyebrow">SERVICE INTEGRATION PENDING</span>
                  <h2>
                    Every presence
                    <br />
                    has a story.
                  </h2>
                  <p>
                    The attendance service will connect class participation with
                    reviewable records. This foundation has no attendance
                    collection or automated student decisions.
                  </p>
                  <Link href="/setup" className="button secondary">
                    View implementation status
                    <Icon name="arrow" size={17} />
                  </Link>
                </div>
              </section>
              <div className="roadmap-grid">
                <article className="panel roadmap-card">
                  <span className="stat-icon green">
                    <Icon name="clock" />
                  </span>
                  <h3>Session records</h3>
                  <p>Join and leave events tied to the classroom session.</p>
                  <span className="tag">Planned</span>
                </article>
                <article className="panel roadmap-card">
                  <span className="stat-icon lavender">
                    <Icon name="users" />
                  </span>
                  <h3>Teacher review</h3>
                  <p>
                    A review workflow for attendance exceptions and corrections.
                  </p>
                  <span className="tag">Planned</span>
                </article>
                <article className="panel roadmap-card">
                  <span className="stat-icon peach">
                    <Icon name="shield" />
                  </span>
                  <h3>Clear evidence</h3>
                  <p>Transparent records with institution-controlled access.</p>
                  <span className="tag">Planned</span>
                </article>
              </div>
            </>
          )}

          {page === "setup" && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">MAKE THIS SPACE YOURS</div>
                  <h1>Workspace setup.</h1>
                  <p>
                    Connect your services and see exactly what the foundation
                    supports.
                  </p>
                </div>
                <button className="button secondary" onClick={app.refresh}>
                  <Icon name="refresh" size={17} />
                  Check connections
                </button>
              </div>
              <InstitutionSetup onSignIn={() => setSignInOpen(true)} />
              <div className="setup-grid">
                <section className="panel setup-panel">
                  <div className="section-heading">
                    <h2>Connect your workspace</h2>
                    <span className="mini-count">{readySteps}/4</span>
                  </div>
                  <SetupSteps />
                  <div className="setup-actions">
                    {!app.session && (
                      <button
                        className="button primary"
                        onClick={() => setSignInOpen(true)}
                      >
                        <Icon name="lock" size={17} />
                        Sign in to continue
                      </button>
                    )}
                    <button
                      className="button secondary"
                      onClick={() => app.setPreview(!app.preview)}
                    >
                      <Icon name="eye" size={17} />
                      {app.preview
                        ? "Exit design preview"
                        : "Explore design preview"}
                    </button>
                  </div>
                </section>
                <section className="panel connections-panel">
                  <h2>Service connections</h2>
                  <div className="connection-row">
                    <span>FastAPI backend</span>
                    <span
                      className={`status-label ${app.apiStatus === "online" ? "ready" : "pending"}`}
                    >
                      {app.apiStatus === "online"
                        ? "Reachable"
                        : app.apiStatus === "checking"
                          ? "Checking"
                          : "Unavailable"}
                    </span>
                  </div>
                  <code className="endpoint">{API_URL}</code>
                  <div className="connection-row">
                    <span>Frontend auth settings</span>
                    <span
                      className={`status-label ${authConfigured ? "ready" : "pending"}`}
                    >
                      {authConfigured ? "Configured" : "Not configured"}
                    </span>
                  </div>
                  <div className="connection-row">
                    <span>Backend auth settings</span>
                    <span
                      className={`status-label ${app.capabilities?.authentication_configured ? "ready" : "pending"}`}
                    >
                      {app.capabilities
                        ? app.capabilities.authentication_configured
                          ? "Configured"
                          : "Not configured"
                        : "Unknown"}
                    </span>
                  </div>
                  <p className="fine-print">
                    Configuration status confirms settings are present. A
                    successful sign-in and profile request confirm access.
                  </p>
                </section>
              </div>
              <section className="panel capability-panel">
                <div className="section-heading">
                  <div>
                    <h2>Feature readiness</h2>
                    <p>
                      {app.capabilities
                        ? "Reported by the connected API."
                        : "API status is unavailable. Planned capabilities remain visible below."}
                    </p>
                  </div>
                  <span className="stage-tag">Community setup</span>
                </div>
                <div className="capability-table">
                  <div className="capability-row">
                    <b>Class planning</b>
                    <p>List and create institution-scoped class plans.</p>
                    <span
                      className={`status-label ${app.capabilities?.features.class_planning ? "ready" : "pending"}`}
                    >
                      {app.capabilities?.features.class_planning
                        ? "Implemented"
                        : "Awaiting API"}
                    </span>
                  </div>
                  {(
                    [
                      [
                        "institution_management",
                        "Institution management",
                        "Create a workspace and manage member roles and access.",
                      ],
                      [
                        "invitations",
                        "Invitations",
                        "Personal links for teachers and students to join your institution.",
                      ],
                      [
                        "enrollment",
                        "Class enrollment",
                        "Give enrolled students access to their class timetable.",
                      ],
                      [
                        "verified_entry",
                        "Verified entry",
                        "Identity and entry verification workflows.",
                      ],
                      [
                        "live_video",
                        "Live video",
                        "Real-time classroom media and meeting controls.",
                      ],
                      [
                        "attendance",
                        "Attendance",
                        "Session events, records, and review workflows.",
                      ],
                      [
                        "polls",
                        "Classroom polls",
                        "Live questions and synchronized responses.",
                      ],
                    ] as const
                  ).map(([key, title, description]) => (
                    <div className="capability-row" key={key}>
                      <b>{title}</b>
                      <p>{description}</p>
                      <span
                        className={`status-label ${app.capabilities?.features[key] ? "ready" : "pending"}`}
                      >
                        {app.capabilities?.features[key]
                          ? "API reports ready"
                          : "Planned"}
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            </>
          )}
          <footer className="page-footer">
            <span>
              ClassGuard AI <span>·</span> A focused place to learn
            </span>
            <span>Community setup · v0.2</span>
          </footer>
        </main>
      </div>

      {signInOpen && <SignInModal onClose={() => setSignInOpen(false)} />}
      {createOpen && canCreate && (
        <CreateClassModal
          key={`${app.session?.user.id}:${app.institution?.institution_id}`}
          onClose={() => setCreateOpen(false)}
          onCreated={(item) => {
            app.refreshClasses();
            setNotice(`“${item.title}” was saved to your institution.`);
          }}
        />
      )}
      {selectedClass &&
        (app.preview ||
          selectedClass.institution_id === app.institution?.institution_id) && (
          <Modal
            title={selectedClass.title}
            onClose={() => setSelectedClass(null)}
          >
            <div className="detail-labels">
              <span className="tag">{selectedClass.subject}</span>
              <span className="stage-tag">
                {app.preview ? "Sample class plan" : "Class plan"}
              </span>
            </div>
            <dl className="class-details">
              <div>
                <dt>
                  <Icon name="calendar" size={17} />
                  Starts
                </dt>
                <dd>{formatDate(selectedClass.starts_at, true)}</dd>
              </div>
              <div>
                <dt>
                  <Icon name="clock" size={17} />
                  Duration
                </dt>
                <dd>{selectedClass.duration_minutes} minutes</dd>
              </div>
            </dl>
            <p className="detail-description">
              {selectedClass.description ||
                "No lesson description has been added."}
            </p>
            <ClassEnrollment classPlan={selectedClass} />
            <div className="notice">
              {app.preview
                ? "This is sample content in the local design preview."
                : "This class plan is saved in your institution."}{" "}
              Live meeting entry will be available after the video service is
              integrated.
            </div>
            <button
              className="button primary full"
              onClick={() => setSelectedClass(null)}
            >
              Back to workspace
            </button>
          </Modal>
        )}
    </div>
  );
}

function SetupSteps({ compact = false }: { compact?: boolean }) {
  const app = useApp();
  const steps = [
    {
      title: "Configure Supabase",
      description:
        "Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY in .env.local.",
      done: authConfigured,
    },
    {
      title: "Connect the API",
      description:
        "Start FastAPI and allow this frontend origin in the backend CORS configuration.",
      done: app.apiStatus === "online",
    },
    {
      title: "Sign in to your account",
      description:
        "Use a real Supabase account created by your institution administrator.",
      done: Boolean(app.session),
    },
    {
      title: "Create or join your institution",
      description:
        "Create a new workspace below, or open the invitation link your administrator shared with you.",
      done: Boolean(app.institution),
    },
  ];
  return (
    <ol className={`setup-steps ${compact ? "compact" : ""}`}>
      {steps.map((step, index) => (
        <li key={step.title} className={step.done ? "done" : ""}>
          <span className="step-number">
            {step.done ? <Icon name="check" size={14} /> : index + 1}
          </span>
          <div>
            <b>{step.title}</b>
            {!compact && <p>{step.description}</p>}
          </div>
          {!compact && (
            <span className={`status-label ${step.done ? "ready" : "pending"}`}>
              {step.done ? "Complete" : "To do"}
            </span>
          )}
        </li>
      ))}
    </ol>
  );
}
