"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { apiRequest } from "@/lib/api";
import { requestMessage, useRequestLifetime } from "@/lib/request-scope";
import type { Invitation, MemberRecord } from "@/lib/types";
import { useApp } from "./app-provider";
import { Icon } from "./icons";
import { Modal } from "./modal";
import { InstitutionSetup } from "./onboarding";

export function memberLabel(member: MemberRecord) {
  return member.email || `Account ${member.user_id.slice(0, 8)}`;
}

export function People({ onSignIn }: { onSignIn: () => void }) {
  const app = useApp();
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">YOUR LEARNING COMMUNITY</div>
          <h1>People, connected.</h1>
          <p>Bring teachers and students into the right workspace.</p>
        </div>
      </div>
      {app.preview ? (
        <section className="panel people-empty">
          <Icon name="users" size={34} />
          <h2>Your community lives here</h2>
          <p>
            Return to your workspace to create an institution, invite people,
            and manage class access.
          </p>
          <button
            className="button secondary"
            onClick={() => app.setPreview(false)}
          >
            Exit design preview
          </button>
        </section>
      ) : app.authLoading || app.profileLoading ? (
        <section className="panel loading-state" role="status">
          <span className="spinner" />
          Loading your institution…
        </section>
      ) : !app.session || !app.institution ? (
        <InstitutionSetup onSignIn={onSignIn} />
      ) : app.institution.role === "student" ? (
        <section className="panel people-empty">
          <Icon name="shield" size={34} />
          <h2>You’re in {app.institution.institution_name}</h2>
          <p>
            Your administrator manages the institution’s people. Your teachers
            share classes with you after enrollment.
          </p>
          <Link href="/classes" className="button primary">
            View my classes
            <Icon name="arrow" size={17} />
          </Link>
        </section>
      ) : (
        <PeopleDirectory
          key={`${app.session.user.id}:${app.institution.institution_id}:${app.institution.role}`}
        />
      )}
    </>
  );
}

function PeopleDirectory() {
  const app = useApp();
  const lifetime = useRequestLifetime();
  const token = app.session!.access_token;
  const institution = app.institution!;
  const admin = institution.role === "admin";
  const base = `/v1/institutions/${encodeURIComponent(institution.institution_id)}`;
  const [members, setMembers] = useState<MemberRecord[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");
  const [version, setVersion] = useState(0);
  const [query, setQuery] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);
  const refresh = useCallback(() => setVersion((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    Promise.all([
      apiRequest<{ items: MemberRecord[] }>(`${base}/members`, {
        token,
        signal: controller.signal,
      }),
      admin
        ? apiRequest<{ items: Invitation[] }>(`${base}/invitations`, {
            token,
            signal: controller.signal,
          })
        : Promise.resolve({ items: [] as Invitation[] }),
    ])
      .then(([members, invitations]) => {
        if (controller.signal.aborted) return;
        setMembers(members.items);
        setInvitations(invitations.items);
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setMembers([]);
          setInvitations([]);
          setError(requestMessage(error, "People could not be loaded."));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [base, token, admin, version]);

  async function updateMember(
    member: MemberRecord,
    change: { role?: "teacher" | "student"; active?: boolean },
  ) {
    if (busy) return;
    const signal = lifetime.current?.signal;
    setBusy(member.user_id);
    setError("");
    setNotice("");
    try {
      await apiRequest<MemberRecord>(
        `${base}/members/${encodeURIComponent(member.user_id)}`,
        { method: "PATCH", token, body: change, signal },
      );
      if (signal?.aborted) return;
      setNotice(
        change.active === false
          ? `${memberLabel(member)} no longer has access to this institution.`
          : change.active === true
            ? `Access restored for ${memberLabel(member)}.`
            : `Role updated for ${memberLabel(member)}.`,
      );
      refresh();
    } catch (error) {
      if (!signal?.aborted)
        setError(requestMessage(error, "The member could not be updated."));
    } finally {
      if (!signal?.aborted) setBusy("");
    }
  }

  async function revoke(invitation: Invitation) {
    if (busy) return;
    const signal = lifetime.current?.signal;
    setBusy(invitation.id);
    setError("");
    setNotice("");
    try {
      await apiRequest<Invitation>(
        `${base}/invitations/${encodeURIComponent(invitation.id)}/revoke`,
        { method: "POST", token, signal },
      );
      if (signal?.aborted) return;
      setNotice(`Invitation for ${invitation.email} revoked.`);
      refresh();
    } catch (error) {
      if (!signal?.aborted)
        setError(requestMessage(error, "The invitation could not be revoked."));
    } finally {
      if (!signal?.aborted) setBusy("");
    }
  }
  const filtered = members.filter((member) =>
    `${member.email || ""} ${member.user_id} ${member.role}`
      .toLocaleLowerCase()
      .includes(query.toLocaleLowerCase()),
  );
  return (
    <>
      <div className="people-summary">
        <div>
          <span className="eyebrow">
            {admin ? "INSTITUTION DIRECTORY" : "STUDENT DIRECTORY"}
          </span>
          <h2>{institution.institution_name}</h2>
          <p>
            {admin
              ? "Invite people, set their roles, and manage access."
              : "Open one of your class plans to enroll students."}
          </p>
        </div>
        <div className="people-heading-actions">
          <button
            className="button secondary"
            onClick={refresh}
            disabled={loading || Boolean(busy)}
            aria-label="Refresh people"
          >
            <Icon name="refresh" size={17} />
            Refresh
          </button>
          {admin && (
            <button
              className="button primary"
              onClick={() => setInviteOpen(true)}
            >
              <Icon name="plus" size={17} />
              Invite person
            </button>
          )}
        </div>
      </div>
      {error && (
        <div className="notice error" role="alert">
          {error}
          <button onClick={refresh}>Retry</button>
        </div>
      )}
      {notice && (
        <div className="notice success" role="status">
          <Icon name="check" size={17} />
          {notice}
        </div>
      )}
      <section className="panel directory-panel">
        <div className="class-toolbar">
          <div className="section-heading">
            <h2>{admin ? "Members" : "Students"}</h2>
            <span className="count-pill">{members.length}</span>
          </div>
          <label className="search-field">
            <Icon name="search" size={18} />
            <span className="sr-only">Search people</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search email or role"
            />
          </label>
        </div>
        {loading ? (
          <div className="loading-state" role="status">
            <span className="spinner" />
            Loading people…
          </div>
        ) : filtered.length ? (
          <ul className="member-list">
            {filtered.map((member) => (
              <MemberRow
                key={`${member.user_id}:${member.role}:${member.active}`}
                member={member}
                editable={admin && member.role !== "admin"}
                busy={Boolean(busy)}
                pending={busy === member.user_id}
                onUpdate={(change) => updateMember(member, change)}
              />
            ))}
          </ul>
        ) : (
          <div className="people-empty">
            <Icon name="users" size={30} />
            <h3>{query ? "No matching people" : "Room for your community"}</h3>
            <p>
              {query
                ? "Try another email address or role."
                : admin
                  ? "Teachers and students appear here after they accept an invitation."
                  : "Your administrator can invite students to this institution."}
            </p>
          </div>
        )}
        {admin && (
          <p className="fine-print">
            Administrator roles are protected. Changing a role clears that
            person’s student enrollments. Removing access preserves enrollments
            for restoration and takes effect on the next request.
          </p>
        )}
      </section>
      {admin && (
        <section className="panel invitations-panel">
          <div className="section-heading">
            <div>
              <h2>Invitations</h2>
              <p>Share each link with the person it was created for.</p>
            </div>
            <span className="count-pill">
              {
                invitations.filter(
                  (invitation) => invitation.status === "pending",
                ).length
              }{" "}
              pending
            </span>
          </div>
          {loading ? (
            <p className="muted" role="status">
              Loading invitations…
            </p>
          ) : invitations.length ? (
            <ul className="member-list">
              {invitations.map((invitation) => (
                <li className="member-row" key={invitation.id}>
                  <span className="member-avatar">
                    <Icon name="mail" size={18} />
                  </span>
                  <div className="member-identity">
                    <b>{invitation.email}</b>
                    <span>
                      {invitation.role} ·{" "}
                      {invitation.status === "pending" ? "Expires" : "Expiry"}{" "}
                      {new Date(invitation.expires_at).toLocaleDateString(
                        undefined,
                        { day: "numeric", month: "short", year: "numeric" },
                      )}
                    </span>
                  </div>
                  <div className="member-actions">
                    <span
                      className={`status-label ${invitation.status === "accepted" ? "ready" : "pending"}`}
                    >
                      {invitation.status}
                    </span>
                    {invitation.status === "pending" && (
                      <button
                        className="button subtle small"
                        disabled={Boolean(busy)}
                        aria-label={`Revoke invitation for ${invitation.email}`}
                        onClick={() => revoke(invitation)}
                      >
                        {busy === invitation.id ? "Revoking…" : "Revoke"}
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="people-empty compact">
              <p>
                No invitations yet. Invite a teacher or student to get started.
              </p>
            </div>
          )}
          <p className="fine-print">
            Links expire after 7 days and can be used once by the matching
            account. A new invitation replaces any pending invitation for the
            same email. No email is sent automatically.
          </p>
        </section>
      )}
      {inviteOpen && (
        <InvitePersonModal
          onClose={() => setInviteOpen(false)}
          onCreated={refresh}
        />
      )}
    </>
  );
}

function MemberRow({
  member,
  editable,
  busy,
  pending,
  onUpdate,
}: {
  member: MemberRecord;
  editable: boolean;
  busy: boolean;
  pending: boolean;
  onUpdate: (change: {
    role?: "teacher" | "student";
    active?: boolean;
  }) => void;
}) {
  const [role, setRole] = useState(member.role);
  return (
    <li className={`member-row ${member.active ? "" : "inactive-member"}`}>
      <span className="member-avatar">
        {(member.email || "U")[0].toUpperCase()}
      </span>
      <div className="member-identity">
        <b title={member.email || member.user_id}>{memberLabel(member)}</b>
        <span>
          {member.role} · {member.active ? "Active" : "Access removed"}
        </span>
        {!member.email && (
          <small>Email appears after this account signs in.</small>
        )}
      </div>
      <div className="member-actions">
        {editable ? (
          <>
            <label className="sr-only" htmlFor={`role-${member.user_id}`}>
              Role for {memberLabel(member)}
            </label>
            <select
              id={`role-${member.user_id}`}
              value={role}
              disabled={busy}
              onChange={(event) =>
                setRole(event.target.value as "teacher" | "student")
              }
            >
              <option value="student">Student</option>
              <option value="teacher">Teacher</option>
            </select>
            {role !== member.role && (
              <button
                className="button secondary small"
                disabled={busy}
                onClick={() =>
                  onUpdate({ role: role as "teacher" | "student" })
                }
              >
                Save role
              </button>
            )}
            <button
              className="button subtle small"
              disabled={busy}
              onClick={() => onUpdate({ active: !member.active })}
              aria-label={`${member.active ? "Remove" : "Restore"} access for ${memberLabel(member)}`}
            >
              {pending
                ? "Saving…"
                : member.active
                  ? "Remove access"
                  : "Restore access"}
            </button>
          </>
        ) : (
          <span className="tag">
            {member.role === "admin" ? "Administrator" : "Student"}
          </span>
        )}
      </div>
    </li>
  );
}

function InvitePersonModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const app = useApp();
  const lifetime = useRequestLifetime();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<Invitation | null>(null);
  const [inviteLink, setInviteLink] = useState("");
  const [copyStatus, setCopyStatus] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!app.session || !app.institution || busy) return;
    const fields = new FormData(event.currentTarget);
    const signal = lifetime.current?.signal;
    setBusy(true);
    setError("");
    try {
      const invitation = await apiRequest<Invitation & { token: string }>(
        `/v1/institutions/${encodeURIComponent(app.institution.institution_id)}/invitations`,
        {
          token: app.session.access_token,
          method: "POST",
          signal,
          body: {
            email: String(fields.get("email") || "").trim(),
            role: String(fields.get("role")),
          },
        },
      );
      if (signal?.aborted) return;
      const link = new URL("/join", window.location.origin);
      link.hash = new URLSearchParams({ token: invitation.token }).toString();
      setInviteLink(link.toString());
      const { token: _token, ...details } = invitation;
      setCreated(details);
      onCreated();
    } catch (error) {
      if (!signal?.aborted)
        setError(requestMessage(error, "The invitation could not be created."));
    } finally {
      if (!signal?.aborted) setBusy(false);
    }
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(inviteLink);
      if (!lifetime.current?.signal.aborted)
        setCopyStatus("Invitation link copied.");
    } catch {
      if (!lifetime.current?.signal.aborted)
        setCopyStatus("Select the link below and copy it manually.");
    }
  }
  return (
    <Modal
      title={
        created ? "Your invitation is ready" : "Invite to your institution"
      }
      onClose={onClose}
    >
      {created ? (
        <>
          <p className="modal-intro">
            Share this link with{" "}
            <strong className="wrap-anywhere">{created.email}</strong>. They
            will join as a {created.role} after signing in with that email.
          </p>
          <div className="form-stack">
            <label>
              Invitation link
              <input
                readOnly
                value={inviteLink}
                onFocus={(event) => event.currentTarget.select()}
                spellCheck={false}
                autoComplete="off"
              />
            </label>
            <button className="button primary" onClick={copy}>
              Copy invitation link
              <Icon name="arrow" size={17} />
            </button>
            {copyStatus && (
              <p className="notice success" role="status">
                {copyStatus}
              </p>
            )}
          </div>
          <p className="fine-print">
            Expires {new Date(created.expires_at).toLocaleString()}. Copy it
            before closing this window; it won’t be shown again. This link uses
            the current website address. For another device, open ClassGuard at
            its shared HTTPS address before creating the link.
          </p>
          <button className="button secondary full" onClick={onClose}>
            Done
          </button>
        </>
      ) : (
        <>
          <p className="modal-intro">
            Invite a teacher or student to {app.institution?.institution_name}.
            Make sure their account has been created before sharing the link.
          </p>
          <form className="form-stack" onSubmit={submit}>
            <label>
              Email address
              <input
                name="email"
                type="email"
                autoComplete="off"
                placeholder="person@school.edu"
                required
                maxLength={254}
                disabled={busy}
              />
            </label>
            <label>
              Institution role
              <select name="role" defaultValue="student" disabled={busy}>
                <option value="student">Student</option>
                <option value="teacher">Teacher</option>
              </select>
            </label>
            <p className="field-help">
              Teachers can plan classes and enroll students. Students see
              classes they’re enrolled in.
            </p>
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <button className="button primary" disabled={busy}>
              {busy ? "Creating invitation…" : "Create invitation link"}
              <Icon name="plus" size={17} />
            </button>
          </form>
          <p className="fine-print">
            You’ll get a link to share yourself. No email is sent. It expires
            after 7 days; a new link replaces any pending invitation for this
            email.
          </p>
        </>
      )}
    </Modal>
  );
}
